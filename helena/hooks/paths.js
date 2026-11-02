// Where Helena keeps the user's data. Everything learned lives here, outside the plugin, so updates never wipe it.
//   ~/.helena/vault        one line: path of the Obsidian vault (default ~/Helena)
//   ~/.helena/kits.json    the user's kits (see helena/kits.example.json)
//   ~/.helena/library/     skills that only load when a kit asks for them
//   ~/.helena/audit.jsonl  every time a hook blocked or asked about something (/helena:audit, exportable for a team)
//   ~/.helena/egress.jsonl every host, search and MCP server the AI reached (/helena:audit lists them)
//   ~/.helena/events.jsonl what went right, for the app (helena/app): done checks that passed, notes and kits handed over
const fs = require('fs'), path = require('path'), os = require('os'), { spawn } = require('child_process');
const HOME = path.join(os.homedir(), '.helena');
const readVault = () => { try { return fs.readFileSync(path.join(HOME, 'vault'), 'utf8').trim(); } catch {} };
const VAULT = process.env.HELENA_VAULT || readVault() || path.join(os.homedir(), 'Helena');
// runs a helena/*.py script detached, output appended to ~/.helena/<log>; the hook exits right away
const bg = (script, args, log) => {
  fs.mkdirSync(HOME, { recursive: true });
  const fd = fs.openSync(path.join(HOME, log), 'a');
  spawn('python', [path.join(__dirname, '..', script), ...args], {
    detached: true, windowsHide: true, stdio: ['ignore', fd, fd],
    env: { ...process.env, HELENA_DISTILLING: '1', PYTHONIOENCODING: 'utf-8' },
  }).unref();
};
// same pattern as guard.js and distill.py (SECRET)
const SECRET = /\b(sk[_-][A-Za-z0-9_-]{16,}|[a-f0-9]{40,}|(pk|rk)_(live|test)_[A-Za-z0-9]{10,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|\d{8,}:[A-Za-z0-9_-]{30,}|(AKIA|ASIA)[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{10,})/g;
// one line per hook decision; what was attempted is cut short and keys are masked
const audit = (ev, hook, decision, why) => {
  try {
    const t = ev.tool_input || {};
    fs.mkdirSync(HOME, { recursive: true });
    fs.appendFileSync(path.join(HOME, 'audit.jsonl'), JSON.stringify({
      ts: new Date().toISOString().slice(0, 19), project: path.basename(ev.cwd || process.cwd()), session: ev.session_id || '',
      hook, tool: ev.tool_name || '', decision,
      what: String(t.command || t.file_path || t.pattern || '').slice(0, 160).replace(SECRET, '***'),
      why: String(why).split('\n')[0].slice(0, 200),
    }) + '\n');
  } catch {}
};
// where the AI reached outside this machine: a fetched host, a web search, an MCP server, a URL in a command
const egress = (ev, to) => {
  try {
    fs.mkdirSync(HOME, { recursive: true });
    fs.appendFileSync(path.join(HOME, 'egress.jsonl'), JSON.stringify({
      ts: new Date().toISOString().slice(0, 19), project: path.basename(ev.cwd || process.cwd()), session: ev.session_id || '',
      tool: ev.tool_name || '', to: String(to).split('@').pop().slice(0, 80),  // user:password@host keeps the host only
    }) + '\n');
  } catch {}
};
// one line per thing the app shows that is not a block: { ts, project, session, kind, ...data }
const event = (ev, kind, data) => {
  try {
    fs.mkdirSync(HOME, { recursive: true });
    fs.appendFileSync(path.join(HOME, 'events.jsonl'), JSON.stringify({
      ts: new Date().toISOString().slice(0, 19), project: path.basename(ev.cwd || process.cwd()), session: ev.session_id || '', kind, ...data,
    }) + '\n');
  } catch {}
};
// what the AI did since the user's last message: its blocks (text, tool_use) newest first, and which tool calls came back
// as errors (tool_use_id -> true) and a short print of what each returned (`seen`, to tell a loop from a poll). Reads the transcript from the end: it reaches megabytes and the Stop hooks run on every
// turn, so parsing all of it each time was the slowest thing Helena did.
const turn = transcript => {
  const fd = fs.openSync(transcript, 'r'), size = fs.fstatSync(fd).size;
  try {
    for (let n = 1 << 20; ; n *= 4) {
      const len = Math.min(n, size), buf = Buffer.alloc(len), blocks = [], failed = {}, seen = {};
      fs.readSync(fd, buf, 0, len, size - len);
      const lines = buf.toString('utf8').split('\n');
      if (len < size) lines.shift();  // cut in half
      for (const line of lines.reverse()) {
        let d;
        try { d = JSON.parse(line); } catch { continue; }
        const c = d.message && d.message.content;
        if (d.type === 'user' && (typeof c === 'string' || (Array.isArray(c) && c.some(b => b.type === 'text')))) return { blocks, failed, seen };
        if (d.type === 'user' && Array.isArray(c)) for (const b of c) if (b.type === 'tool_result') { if (b.is_error) failed[b.tool_use_id] = true; seen[b.tool_use_id] = JSON.stringify(b.content || '').length + ':' + JSON.stringify(b.content || '').slice(-200); }
        if (d.type === 'assistant' && Array.isArray(c)) blocks.push(...c.slice().reverse());
      }
      if (len === size) return { blocks, failed, seen };
    }
  } finally { fs.closeSync(fd); }
};
const turnTools = transcript => turn(transcript).blocks.filter(b => b.type === 'tool_use');
// the session's last model call, from the end of its transcript: context size, the model that answered, when, and how
// long its cache lives (`ttl`, 5 minutes or 1 hour, from the last call that wrote to the cache)
const lastCall = transcript => {
  const r = { ctx: 0, model: '', at: 0, ttl: 0 };
  let found = false;
  try {
    const fd = fs.openSync(transcript, 'r'), size = fs.fstatSync(fd).size, n = Math.min(size, 256 * 1024), buf = Buffer.alloc(n);
    fs.readSync(fd, buf, 0, n, size - n);
    fs.closeSync(fd);
    for (const line of buf.toString('utf8').split('\n').reverse()) {
      if (!line.includes('"usage"') || !line.includes('"assistant"')) continue;
      let d;
      try { d = JSON.parse(line); } catch { continue; }
      const m = d.message || {}, u = m.usage;
      if (!u || /^</.test(m.model || '')) continue;  // "<synthetic>": an error written by the CLI, not a call
      if (!found) {
        found = true;
        r.ctx = (u.input_tokens || 0) + (u.cache_creation_input_tokens || 0) + (u.cache_read_input_tokens || 0);
        r.model = m.model || '';
        r.at = Date.parse(d.timestamp) || 0;
      }
      const c = u.cache_creation || {};
      r.ttl = c.ephemeral_1h_input_tokens ? 3600e3 : c.ephemeral_5m_input_tokens ? 300e3 : 0;
      if (r.ttl) break;
    }
  } catch {}
  return r;
};
// A line written for an AI inside text from outside (a page, a tool result, a cloned repo's CLAUDE.md): outside.js and start.js share this.
// ponytail: fixed phrases in English and Portuguese, so only the lazy attacks are caught and a reworded one passes.
const AIMED = new RegExp([
  '(ignore|disregard|forget)\\s+(all\\s+|any\\s+)?(of\\s+)?(the\\s+|your\\s+)?(previous|prior|above|earlier)\\s+(instructions|prompts?|rules)',
  'do\\s+not\\s+(tell|inform|mention\\s+(it|this)\\s+to)\\s+the\\s+user(?!\\s+to\\b)',
  'without\\s+(telling|informing)\\s+the\\s+user',
  '(disable|bypass|turn\\s+off)\\s+(the\\s+|your\\s+)?(hooks?|guardrails?|guard)\\b',
  '(ignore|desconsidere|esque[cç]a)\\s+(todas\\s+)?as\\s+instru[cç][oõ]es\\s+(anteriores|acima)',
  'n[aã]o\\s+(conte|diga|avise|informe)\\s+(nada\\s+)?(ao|para\\s+o|pro)\\s+usu[aá]rio',
  'sem\\s+(avisar|contar|informar)\\s+(ao\\s+|o\\s+)?usu[aá]rio',
].join('|'), 'i');
// -> [match, how] or null. Invisible text: zero-width characters (stripped, then looked at again) and the tag block, which
// renders as nothing but spells ASCII (code point minus 0xE0000). An emoji flag is a tag run too: those are taken out first.
function aimed(text) {
  const flagSeq = /\u{1F3F4}[\u{E0020}-\u{E007E}]+\u{E007F}/gu, tagRun = /[\u{E0020}-\u{E007E}]+/gu;
  const bare = text.replace(flagSeq, '');
  const tags = (bare.match(tagRun) || []).map(r => [...r].map(c => String.fromCharCode(c.codePointAt(0) - 0xE0000)).join(''));
  const stripped = text.replace(/[​-‏⁠-⁤﻿]/g, '');
  let m = text.match(AIMED), how = '';
  if (m) { const c = text.match(/<!--[\s\S]*?-->/g); if (c && c.some(x => AIMED.test(x))) how = ' hidden inside an HTML comment'; }
  else if ((m = stripped.match(AIMED))) how = ' hidden with zero-width characters';
  else if ((m = tags.join(' ').match(AIMED))) how = ' spelled in invisible Unicode tag characters';
  else if (tags.some(r => r.length > 3)) m = [tags.find(r => r.length > 3)], how = ' (invisible Unicode tag characters, text a reader cannot see)';
  else if (/[A-Za-z][​‌‍⁠-⁤﻿]+[A-Za-z]/.test(text)) m = ['zero-width characters inside a word'], how = ' (zero-width characters hiding text)';
  return m ? [m, how] : null;
}
// `tests: spec-only` in <repo>/.helena/delegate or ~/.helena/delegate (same lookup as delegate.js config(): the first file found decides)
const specOnly = cwd => {
  let root = cwd;
  try { root = require('child_process').execSync('git rev-parse --show-toplevel', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500 }).trim(); } catch {}
  for (const f of [path.join(root, '.helena', 'delegate'), path.join(HOME, 'delegate')]) {
    let text;
    try { text = fs.readFileSync(f, 'utf8'); } catch { continue; }
    return /^\s*tests\s*:\s*spec-only/mi.test(text);
  }
  return false;
};
// the project's test command (done.js runs it, nudge.js names it). The first line of <repo>/.helena/test (a command, or
// "off"), else what the project has: package.json "test" → npm test, pytest config → pytest, Cargo, go.mod, tsconfig → tsc
function testCommand(root) {
  const set = (() => { try { return fs.readFileSync(path.join(root, '.helena', 'test'), 'utf8').split('\n').map(l => l.trim()).find(l => l && !l.startsWith('#')); } catch {} })();
  if (set) return /^off$/i.test(set) ? '' : set;
  const has = f => fs.existsSync(path.join(root, f));
  try {
    const t = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8')).scripts.test;
    if (t && !/no test specified/.test(t)) return 'npm test --silent';
  } catch {}
  if (['pytest.ini', 'conftest.py', 'tests/conftest.py'].some(has) || (has('tests') && /\[tool\.pytest|pytest/.test((() => { try { return fs.readFileSync(path.join(root, 'pyproject.toml'), 'utf8'); } catch { return ''; } })())))
    return 'python -m pytest -q -x';
  if (has('Cargo.toml')) return 'cargo test -q';
  if (has('go.mod')) return 'go test ./...';
  if (has('tsconfig.json') && has('node_modules/typescript')) return 'npx tsc --noEmit';
  return '';
}
// assertions and skips in test code: an edit that removes the first or adds the second weakens the tests (gate.js, done.js)
const ASSERT = /\bassert\w*\b|\bexpect\s*\(|\.should\b|\.to(Be|Equal|StrictEqual|Have|Throw|Match|Contain)\w*\s*\(/g;
const SKIP = /\b(it|test|describe)\.(skip|todo)\b|\bx(it|describe|test)\s*\(|@pytest\.mark\.(skip|xfail)|\bpytest\.skip\(|@unittest\.skip|\bt\.Skip\(|#\[ignore\]/g;
// a code file (done.js runs the tests when one was edited)
const CODE = /\.(js|jsx|ts|tsx|mjs|cjs|py|go|rs|java|kt|rb|php|cs|c|cc|cpp|h|swift|vue|svelte|astro)$/i;
// a command the AI ran that checks code: what a test run looks like in a transcript
const TESTISH = /\b(test|tests|pytest|jest|vitest|mocha|unittest|tsc|cargo\s+check|go\s+vet|tox|nox|phpunit|rspec)\b|\btest_\w+|\w_test\b|\.(test|spec)\.\w+/i;
const TEST = /(^|[\\/])(tests?|__tests__|spec)[\\/]|[._-](test|spec)\.[a-z]+$|(^|[\\/])test_[^\\/]+\.py$|_test\.(go|py)$/i;
module.exports = { ASSERT, SKIP, CODE, TEST, TESTISH, testCommand, specOnly, aimed, AIMED, audit, event, bg, egress, turn, turnTools, lastCall, HOME, VAULT, MEMORY: path.join(VAULT, 'Memory'), LIBRARY: path.join(HOME, 'library'), KITS: path.join(HOME, 'kits.json') };
