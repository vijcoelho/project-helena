// How much of each AI plan's usage limit is gone, from what the CLIs already write to disk (no network, no LLM):
//   Claude  rate_limits from the status line JSON, saved by statusline.js to ~/.helena/limits-claude.json
//   Codex   rate_limits in the last token_count event of the newest ~/.codex/sessions rollout (same limit as ChatGPT)
// Antigravity/Gemini keep no usage on disk, so they show up only as an alternative with an unknown limit.
// Besides the % used, the weekly window gets a pace: at the rate spent so far, does it last until it resets?
//   node limits.js     every AI, its windows and the pace (/helena:limits)
// ponytail: newest rollout only; a limit that already reset still reads as used until the next Codex message (resets_at fixes it)
const fs = require('fs'), path = require('path'), os = require('os');
const { HOME } = require('./paths');
const now = () => Date.now() / 1000;
const DAY = 86400, WEEK = 7 * DAY;

// a window: { label, used (0-100), resets_at (unix s, optional), len (seconds) }; one that already reset counts as 0
const live = w => w && !(w.resets_at && w.resets_at < now());
const pct = windows => Math.round(Math.max(0, ...windows.filter(live).map(w => w.used)));

function claude() {
  try {
    const r = JSON.parse(fs.readFileSync(path.join(HOME, 'limits-claude.json'), 'utf8'));
    return Object.entries(r).filter(([, w]) => w).map(([k, w]) => ({
      label: /seven|week/i.test(k) ? 'week' : /five|5h/i.test(k) ? '5h' : k.replace(/_/g, ' '),
      used: w.used_percentage ?? w.used_percent ?? 0, resets_at: w.resets_at, len: /seven|week/i.test(k) ? WEEK : 5 * 3600,
    }));
  } catch {}
}

function codex() {
  let dir = path.join(os.homedir(), '.codex', 'sessions');
  try {
    for (let i = 0; i < 3; i++) dir = path.join(dir, fs.readdirSync(dir).filter(d => /^\d+$/.test(d)).sort().pop());  // YYYY/MM/DD
    const f = fs.readdirSync(dir).filter(f => f.endsWith('.jsonl')).map(f => path.join(dir, f))
      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
    for (const l of fs.readFileSync(f, 'utf8').split('\n').reverse()) if (l.includes('"rate_limits"')) {
      const r = JSON.parse(l).payload.rate_limits;
      return [['5h', r.primary, 300], ['week', r.secondary, 10080]].filter(([, w]) => w).map(([label, w, min]) => ({
        label, used: w.used_percent ?? w.used_percentage ?? 0, resets_at: w.resets_at, len: (w.window_minutes || min) * 60,
      }));
    }
  } catch {}
}

const which = cmd => (process.env.PATH || '').split(path.delimiter)
  .some(d => ['', '.exe', '.cmd'].some(e => fs.existsSync(path.join(d, cmd + e))));
const weekday = t => new Date(t * 1000).toLocaleDateString('en-US', { weekday: 'short', hour: 'numeric' });

// pace of the weekly window: null while it is fine, else { out: unix s when it runs out at this rate, perDay: % per day that lasts }
function pace(windows) {
  const w = (windows || []).find(x => x.label === 'week' && live(x) && x.resets_at);
  if (!w) return null;
  const left = w.resets_at - now(), elapsed = w.len - left;
  if (elapsed < DAY / 2 || w.used < 10) return null;  // too early in the week to tell
  const out = now() + (100 - w.used) / (w.used / elapsed);
  return out < w.resets_at - DAY / 4 ? { out, resets: w.resets_at, used: Math.round(w.used), perDay: Math.max(0, (100 - w.used) / (left / DAY)) } : null;
}

// [{ name, cmd, pct, windows }] for every AI installed; pct undefined = unknown
function all() {
  return [
    { name: 'Claude', cmd: 'claude', windows: claude() },
    { name: 'Codex', cmd: 'codex', windows: codex() },
    { name: 'Antigravity (Gemini)', cmd: 'agy' },
  ].filter(a => which(a.cmd)).map(a => ({ ...a, pct: a.windows ? pct(a.windows) : undefined }));
}

const CONTINUE = '"Read HANDOFF.md and continue from Next"';

// { level, text } for the AI running this session, or null while it still has room
function warn(current, levels = [80, 95]) {
  const list = all(), me = list.find(a => a.cmd === current);
  if (!me || me.pct === undefined || me.pct < levels[0]) return null;
  const free = list.filter(a => a !== me && !(a.pct >= levels[0])).sort((a, b) => (a.pct ?? 50) - (b.pct ?? 50));
  const go = free.length ? free.map(a => `\`${a.cmd}\` (${a.name}${a.pct === undefined ? '' : `, ${a.pct}% used`})`).join(' or ') : '';
  const level = me.pct >= levels[1] ? levels[1] : levels[0];
  return { level, text: `Helena: ${me.name} has used ${me.pct}% of its plan limit. ` + (level === levels[1]
    ? 'Before anything else, write HANDOFF.md (Done / Next / How to run / Decisions). Then tell the user in one line that the ' +
      `limit is about to run out and to continue in ${go || 'another AI'}: Helena hands it the same HANDOFF.md and memory, ` +
      'checks it against the repo and has it restate the next step.' +
      (free.length ? ` Give them the command, ready to paste in this folder: \`${free[0].cmd} ${CONTINUE}\`` : '')
    : 'When this request is done, update HANDOFF.md and tell the user in one line: /clear makes each message cheaper ' +
      `so the limit lasts longer${go ? `, and ${go} has room to continue with the same memory` : ''}.`) };
}

// the weekly pace warning for the AI running this session, or null
function paceWarn(current) {
  const me = all().find(a => a.cmd === current), p = me && pace(me.windows);
  return p && `Helena: ${me.name} has used ${p.used}% of its weekly limit; at this pace it runs out ${weekday(p.out)}, ` +
    `before it resets ${weekday(p.resets)}. When this request is done, tell the user in one line: about ${Math.round(p.perDay)}% ` +
    'a day lasts the week, and short sessions (HANDOFF.md + /clear) stretch it furthest.';
}

module.exports = { all, warn, pace, paceWarn };
if (require.main === module) {
  const list = all();
  if (!list.length) console.log('No AI CLI found on PATH.');
  for (const a of list) {
    const ws = (a.windows || []).map(w => `${w.label} ${live(w) ? Math.round(w.used) : 0}%` +
      (w.resets_at && live(w) ? ` (resets ${weekday(w.resets_at)})` : '')).join(', ');
    const p = pace(a.windows);
    console.log(`${a.name.padEnd(22)} ${ws || 'usage unknown (this CLI keeps none on disk)'}` +
      (p ? `\n${''.padEnd(22)} at this pace the week runs out ${weekday(p.out)}; ~${Math.round(p.perDay)}%/day lasts until the reset`
        : (a.windows || []).some(w => w.label === 'week') ? `\n${''.padEnd(22)} on pace for the week` : ''));
  }
}
