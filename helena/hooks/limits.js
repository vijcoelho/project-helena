// How much of each AI plan's usage limit is gone, from what the CLIs already write to disk (no network, no LLM):
//   Claude  rate_limits from the status line JSON, saved by statusline.js to ~/.helena/limits-claude.json
//   Codex   rate_limits in the last token_count event of the newest ~/.codex/sessions rollout (same limit as ChatGPT)
// Antigravity/Gemini keep no usage on disk, so they show up only as an alternative with an unknown limit.
// ponytail: newest rollout only; a limit that already reset still reads as used until the next Codex message (resets_at fixes it)
const fs = require('fs'), path = require('path'), os = require('os');
const { HOME } = require('./paths');
const now = () => Date.now() / 1000;

// a window that already reset counts as 0
const pct = windows => Math.round(Math.max(0, ...windows.filter(w => w && !(w.resets_at && w.resets_at < now()))
  .map(w => w.used_percentage ?? w.used_percent ?? 0)));

function claude() {
  try { return pct(Object.values(JSON.parse(fs.readFileSync(path.join(HOME, 'limits-claude.json'), 'utf8')))); } catch {}
}

function codex() {
  let dir = path.join(os.homedir(), '.codex', 'sessions');
  try {
    for (let i = 0; i < 3; i++) dir = path.join(dir, fs.readdirSync(dir).filter(d => /^\d+$/.test(d)).sort().pop());  // YYYY/MM/DD
    const f = fs.readdirSync(dir).filter(f => f.endsWith('.jsonl')).map(f => path.join(dir, f))
      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
    const lines = fs.readFileSync(f, 'utf8').split('\n').reverse();
    for (const l of lines) if (l.includes('"rate_limits"')) {
      const r = JSON.parse(l).payload.rate_limits;
      return pct([r.primary, r.secondary]);
    }
  } catch {}
}

const which = cmd => (process.env.PATH || '').split(path.delimiter)
  .some(d => ['', '.exe', '.cmd'].some(e => fs.existsSync(path.join(d, cmd + e))));

// [{ name, cmd, pct }] for every AI installed; pct undefined = unknown
function all() {
  return [
    { name: 'Claude', cmd: 'claude', pct: claude() },
    { name: 'Codex', cmd: 'codex', pct: codex() },
    { name: 'Antigravity (Gemini)', cmd: 'agy' },
  ].filter(a => which(a.cmd));
}

// { level, text } for the AI running this session, or null while it still has room
function warn(current, levels = [80, 95]) {
  const list = all(), me = list.find(a => a.cmd === current);
  if (!me || me.pct === undefined || me.pct < levels[0]) return null;
  const free = list.filter(a => a !== me && !(a.pct >= levels[0])).sort((a, b) => (a.pct ?? 50) - (b.pct ?? 50));
  const go = free.length ? free.map(a => `\`${a.cmd}\` (${a.name}${a.pct === undefined ? '' : `, ${a.pct}% used`})`).join(' or ') : '';
  const level = me.pct >= levels[1] ? levels[1] : levels[0];
  return { level, text: `Helena: ${me.name} has used ${me.pct}% of its plan limit. ` + (level === levels[1]
    ? 'Before anything else, write HANDOFF.md (Done / Next / How to run / Decisions). Then tell the user in one line that the ' +
      `limit is about to run out and to continue in ${go || 'another AI'}: Helena hands it the same HANDOFF.md and memory.`
    : 'When this request is done, update HANDOFF.md and tell the user in one line: /clear makes each message cheaper ' +
      `so the limit lasts longer${go ? `, and ${go} has room to continue with the same memory` : ''}.`) };
}

module.exports = { all, warn };
if (require.main === module) for (const a of all()) console.log(`${a.name}: ${a.pct === undefined ? 'unknown' : a.pct + '%'}`);
