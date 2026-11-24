// Low-volume lifecycle hooks (0 fixed tokens at session start):
//  - PreModelSwitch: warns before switching models mid-session while >= 40k of prompt cache is still warm
//  - StopFailure: when a turn dies on rate/plan limit, logs it and prints a ready handoff command for another AI
//  - PostToolUseFailure: checks project memory notes for a known fix matching the error signature (Phase 4 extends this)
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { HOME, event, lastCall } = require('./paths');
const { field, notes, mark } = require('./memory');
if (process.env.HELENA_DISTILLING) process.exit(0);

const WARM_FLOOR = 40e3;
const LIMIT_ERR = /\b(rate[_\s-]?limit|429|quota|overloaded|usage limit|limit reached|billing|capacity|5-?hour)\b/i;
const SIG = /(Error:|Exception:|FAIL|FAILED|ENOENT|EACCES|EPERM|SyntaxError|TypeError|ModuleNotFoundError|Cannot find module|command not found|not recognized)/i;

const once = (session, key) => {
  const flag = path.join(HOME, 'warnings', `${session}-${key}`);
  if (fs.existsSync(flag)) return false;
  try { fs.mkdirSync(path.dirname(flag), { recursive: true }); fs.writeFileSync(flag, ''); } catch {}
  return true;
};

function preModelSwitch(ev) {
  if (!ev.transcript_path) return null;
  const { ctx, model, at, ttl } = lastCall(ev.transcript_path);
  const next = ev.to_model || ev.new_model || ev.target_model || ev.model || '';
  if (ctx < WARM_FLOOR || !at || !ttl || Date.now() >= at + ttl) return null;
  if (next && model && next.toLowerCase() === model.toLowerCase()) return null;
  const left = Math.max(1, Math.round((at + ttl - Date.now()) / 60e3));
  return { hookSpecificOutput: { hookEventName: 'PreModelSwitch', additionalContext:
    `Helena / cache: switching model mid-session drops ~${Math.round(ctx / 1000)}k of warm prompt cache (${left} min left), ` +
    'so the next call re-reads the whole history at full price (~10x). Finish this step or save HANDOFF.md + /clear first.' } };
}

function stopFailure(ev) {
  const raw = [ev.error, ev.reason, ev.stop_reason, ev.message].filter(Boolean).join(' ');
  event(ev, 'stop_failure', { reason: raw.slice(0, 160) });
  if (!LIMIT_ERR.test(raw)) return null;
  const me = /[\\/]\.codex[\\/]/.test(ev.transcript_path || '') ? 'codex' : 'claude';
  let hint = '';
  try {
    const w = require('./limits').warn(me);
    if (w && w.text) hint = w.text;
  } catch {}
  return hint || 'Helena / limit: this turn stopped on a rate or plan limit. Save HANDOFF.md (if not already fresh) and continue in another installed AI (`/helena:limits` shows room).';
}

function failureMemory(ev) {
  if (ev.is_interrupt) return null;
  const errText = String(ev.error || ev.tool_error || (ev.tool_response && (ev.tool_response.stderr || ev.tool_response.stdout || ev.tool_response)) || '').trim();
  if (errText.length < 10) return null;
  const lines = errText.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const sigLine = (lines.find(l => SIG.test(l)) || lines[0] || '').slice(0, 140);
  if (!sigLine) return null;
  const cwd = ev.cwd || process.cwd(), session = ev.session_id || 'x';
  const list = notes(cwd);
  // 1. Explicit `error_pattern:` regex in frontmatter (exact procedural match)
  let hit = list.find(n => {
    const p = field(n.text, 'error_pattern');
    if (!p) return false;
    try { return new RegExp(p, 'i').test(errText); } catch { return errText.toLowerCase().includes(p.toLowerCase()); }
  });
  // 2. Fallback: strong token overlap between error signature and project/team notes (>= 3 non-trivial error tokens)
  if (!hit) {
    const toks = [...new Set((sigLine.toLowerCase().match(/[a-z][a-z0-9_-]{3,}/g) || []).filter(w => !/^(error|failed|line|file|command|exit|code|with|from|that|this|into|cannot)$/.test(w)))];
    if (toks.length >= 2) {
      const scored = list.filter(n => n.team || /^project:/m.test(n.text)).map(n => {
        const low = (n.slug + ' ' + n.text.slice(0, 1500)).toLowerCase();
        return { n, score: toks.filter(w => low.includes(w)).length };
      }).filter(x => x.score >= Math.min(3, toks.length)).sort((a, b) => b.score - a.score);
      if (scored.length) hit = scored[0].n;
    }
  }
  if (!hit) return null;
  const hash = crypto.createHash('md5').update(hit.slug + ':' + sigLine.replace(/\d+/g, 'N')).digest('hex').slice(0, 8);
  if (!once(session, 'err-' + hash)) return null;
  event(ev, 'failure_hint', { note: hit.file });
  return { hookSpecificOutput: { hookEventName: 'PostToolUseFailure', additionalContext:
    `Helena / known fix (${hit.file})${mark(hit)}:\n` + hit.text.replace(/^---[\s\S]*?---\n/, '').trim().slice(0, 800) } };
}

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  const kind = ev.hook_event_name || '';
  if (kind === 'PreModelSwitch') {
    const out = preModelSwitch(ev);
    if (out) console.log(JSON.stringify(out));
  } else if (kind === 'StopFailure') {
    const msg = stopFailure(ev);
    if (msg) console.log(msg);
  } else if (kind === 'PostToolUseFailure') {
    const out = failureMemory(ev);
    if (out) console.log(JSON.stringify(out));
  }
});
