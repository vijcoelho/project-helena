// PreToolUse: checks what the AI is about to do, before it happens. No LLM; the only network call is the package registry.
//  - secrets stay out of the context: reading a .env (Read, Grep, cat...) is denied and the reason lists its key names only
//  - new packages: `npm i x` / `pip install x` with a name that does not exist on the registry is denied (AIs invent
//    package names and attackers register them); one that is brand new or barely downloaded asks you first
//  - destructive commands (DROP TABLE, DELETE without WHERE, rm -rf /, git push --force, git reset --hard, a prod database
//    URL...) ask you first, even when permissions would have let them run
//  - tests: an edit that removes assertions from a test file or adds a skip asks you first (agents "fix" tests that way)
//  - the team's policy in <repo>/.helena/policy (versioned with the code):
//      deny: terraform apply        a regex per line; matching commands are denied
//      ask: kubectl                 matching commands ask first
//      mcp: github, helena          only these MCP servers may be used in this repo
// Every decision lands in ~/.helena/audit.jsonl. Local hooks can be turned off by whoever owns the machine: this is a
// guardrail for the AI, not a sandbox.
const fs = require('fs'), path = require('path'), { execSync } = require('child_process');
const { audit } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);

const ENV = /(^|[\\/])\.env(\.[\w-]+)?$/, ENV_OK = /\.env\.(example|sample|template)$/;
const ENV_IN_CMD = /\b(cat|type|Get-Content|gc|less|more|head|tail|bat|grep|rg|findstr|Select-String|sed|awk|strings|xxd)\b[^;&|]*?(?:^|[\s'"=])((?:[^\s'"=;|&]*[\\/])?\.env(?:\.[\w-]+)?)(?=$|[\s'";|&)])/i;
const TEST = /(^|[\\/])(tests?|__tests__|spec)[\\/]|[._-](test|spec)\.[a-z]+$|(^|[\\/])test_[^\\/]+\.py$|_test\.(go|py)$/i;
const ASSERT = /\bassert\w*\b|\bexpect\s*\(|\.should\b|\.to(Be|Equal|StrictEqual|Have|Throw|Match|Contain)\w*\s*\(/g;
const SKIP = /\b(it|test|describe)\.(skip|todo)\b|\bx(it|describe|test)\s*\(|@pytest\.mark\.(skip|xfail)|\bpytest\.skip\(|@unittest\.skip|\bt\.Skip\(|#\[ignore\]/g;
const DANGER = [
  [/\bDROP\s+(TABLE|DATABASE|SCHEMA|USER)\b/i, 'drops a database object'],
  [/\bTRUNCATE\s+(TABLE\s+)?["`\w]/i, 'empties a table'],
  [/\bDELETE\s+FROM\s+[\w."`]+\s*(;|"|'|$)/im, 'DELETE without WHERE'],
  [/\brm\s+(-\w*r\w*|--recursive)\b[^;&|]*\s(\/|~\/?|\*|\.\.?\/?|[A-Za-z]:[\\/]?)(\s|$)/, 'recursive delete of a root, home or parent folder'],
  [/\bRemove-Item\b[^;&|]*-Recurse[^;&|]*\s([A-Za-z]:\\?|~|\\|\/)(\s|$)/i, 'recursive delete of a drive or home folder'],
  [/\bgit\s+push\b[^;&|]*\s(--force(?!-with-lease)|-f)\b/, 'force push rewrites remote history'],
  [/\bgit\s+(reset\s+--hard|clean\s+-\w*f)/, 'throws away uncommitted work'],
  [/\b(prisma\s+migrate\s+reset|db\s+push\s+--force-reset|dropdb|terraform\s+destroy|kubectl\s+delete)\b/, 'destroys data or infrastructure'],
  [/\b(postgres(ql)?|mysql|mongodb(\+srv)?|redis):\/\/\S*prod/i, 'points at a production database'],
];

const deny = (ev, why) => { audit(ev, 'gate', 'deny', why); return { permissionDecision: 'deny', permissionDecisionReason: why }; };
const ask = (ev, why) => { audit(ev, 'gate', 'ask', why); return { permissionDecision: 'ask', permissionDecisionReason: why }; };
const count = (text, re) => (String(text || '').match(re) || []).length;

function envKeys(file) {
  try {
    return fs.readFileSync(file, 'utf8').split('\n').map(l => (l.match(/^\s*(?:export\s+)?([A-Za-z_]\w*)\s*=/) || [])[1]).filter(Boolean);
  } catch { return []; }
}
const envWhy = (file, keys) => `Helena / secrets: ${path.basename(file)} holds secret values, and whatever enters the context ` +
  'can end up in logs, transcripts or a commit. ' + (keys.length ? `Its keys are: ${keys.join(', ')}. ` : '') +
  'Work with the key names; if you need a value checked, ask the user to check it.';

// packages a command installs: [{ eco: 'npm' | 'pypi', name }]
function installs(cmd) {
  const out = [];
  for (const seg of cmd.split(/&&|\|\||;|\|/)) {
    const npm = seg.match(/^\s*(?:npx\s+)?(npm|pnpm|yarn|bun)\s+(?:install|i|add)\b(.*)$/i);
    const pip = seg.match(/^\s*(?:pip3?|python3?\s+-m\s+pip|py\s+-m\s+pip|uv\s+pip)\s+install\b(.*)$/i) || seg.match(/^\s*(?:uv|poetry)\s+add\b(.*)$/i);
    const args = ((npm && npm[2]) || (pip && pip[1]) || '').trim().split(/\s+/).filter(Boolean);
    for (let i = 0; i < args.length; i++) {
      const a = args[i].replace(/^["']|["']$/g, '');
      if (/^-(r|c|e|-requirement|-constraint|-editable|-index-url|-extra-index-url|i)$/.test(a)) { i++; continue; }
      if (a.startsWith('-') || /[:\\]|^\.|^\/|^~/.test(a) || (a.includes('/') && !a.startsWith('@'))) continue;
      if (npm) out.push({ eco: 'npm', name: a.startsWith('@') ? a.split('@').slice(0, 2).join('@') : a.split('@')[0] });
      else out.push({ eco: 'pypi', name: a.split(/[<>=!~\[;@ ]/)[0] });
    }
  }
  return out.filter(p => p.name).slice(0, 6);
}

// { missing } / { young: days } / { few: weekly downloads } / {} (fine or unknown); never throws
async function registry({ eco, name }) {
  const get = async url => { const r = await fetch(url, { signal: AbortSignal.timeout(3000) }); return { status: r.status, body: r.ok ? await r.json() : null }; };
  try {
    if (eco === 'npm') {
      const r = await get(`https://api.npmjs.org/downloads/point/last-week/${name}`);
      if (r.status === 404) return { missing: true };
      return r.body && r.body.downloads < 200 ? { few: r.body.downloads } : {};
    }
    const r = await get(`https://pypi.org/pypi/${encodeURIComponent(name)}/json`);
    if (r.status === 404) return { missing: true };
    const first = Object.values((r.body && r.body.releases) || {}).flat().map(f => Date.parse(f.upload_time_iso_8601)).filter(Boolean).sort()[0];
    const days = first ? (Date.now() - first) / 864e5 : Infinity;
    return days < 30 ? { young: Math.round(days) } : {};
  } catch { return {}; }
}

function policy(cwd) {
  let root = cwd;
  try { root = execSync('git rev-parse --show-toplevel', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500 }).trim(); } catch {}
  let text = '';
  try { text = fs.readFileSync(path.join(root, '.helena', 'policy'), 'utf8'); } catch {}
  const list = key => [...text.matchAll(new RegExp(`^${key}:\\s*(.+)$`, 'gmi'))].map(m => m[1].replace(/\s+#.*$/, '').trim()).filter(Boolean);
  return { deny: list('deny'), ask: list('ask'), mcp: list('mcp').flatMap(l => l.split(/[\s,]+/)).filter(Boolean) };
}
const re = s => { try { return new RegExp(s, 'i'); } catch { return null; } };

async function decide(ev) {
  const t = ev.tool_input || {}, tool = ev.tool_name || '', cwd = ev.cwd || process.cwd();

  if (tool.startsWith('mcp__')) {
    const rules = policy(cwd), server = tool.split('__')[1];
    if (!rules.mcp.length) return null;
    if (!rules.mcp.some(a => server === a || server.endsWith('_' + a)))
      return deny(ev, `Helena / team policy: MCP server "${server}" is not on this repo's list (.helena/policy: mcp: ${rules.mcp.join(', ')}). ` +
        'Do the task another way or ask the user to add it.');
    return null;
  }

  if (tool === 'Read' && t.file_path && ENV.test(t.file_path) && !ENV_OK.test(t.file_path))
    return deny(ev, envWhy(t.file_path, envKeys(path.resolve(cwd, t.file_path))));
  if (tool === 'Grep' && [t.path, t.glob].some(p => p && ENV.test(p) && !ENV_OK.test(p)))
    return deny(ev, envWhy(t.path || t.glob, envKeys(path.resolve(cwd, t.path || '.env'))));

  if (['Edit', 'Write', 'MultiEdit'].includes(tool) && t.file_path && TEST.test(t.file_path)) {
    let before = '', after = '';
    if (tool === 'Edit') { before = t.old_string; after = t.new_string; }
    else if (tool === 'MultiEdit') { before = (t.edits || []).map(e => e.old_string).join('\n'); after = (t.edits || []).map(e => e.new_string).join('\n'); }
    else { try { before = fs.readFileSync(path.resolve(cwd, t.file_path), 'utf8'); } catch {} after = t.content; }
    const lost = count(before, ASSERT) - count(after, ASSERT), skips = count(after, SKIP) - count(before, SKIP);
    if (before && (lost > 0 || skips > 0))
      return ask(ev, `Helena / tests: this edit ${lost > 0 ? `removes ${lost} assertion(s)` : ''}${lost > 0 && skips > 0 ? ' and ' : ''}` +
        `${skips > 0 ? `adds ${skips} skip(s)` : ''} in ${path.basename(t.file_path)}. Making a test pass by weakening it hides the bug. ` +
        'Approve only if the test itself was wrong.');
    return null;
  }

  const cmd = t.command;
  if (!cmd) return null;
  const env = cmd.match(ENV_IN_CMD);
  if (env && !ENV_OK.test(env[2])) return deny(ev, envWhy(env[2], envKeys(path.resolve(cwd, env[2]))));

  const rules = policy(cwd);
  for (const r of rules.deny) if (re(r) && re(r).test(cmd))
    return deny(ev, `Helena / team policy: this repo does not let AIs run commands matching "${r}" (.helena/policy). Ask the user to run it.`);

  const pkgs = installs(cmd);
  if (pkgs.length) {
    const found = await Promise.all(pkgs.map(registry));
    const missing = pkgs.filter((p, i) => found[i].missing);
    if (missing.length)
      return deny(ev, `Helena / packages: ${missing.map(p => `"${p.name}" does not exist on ${p.eco === 'npm' ? 'npm' : 'PyPI'}`).join(', ')}. ` +
        'AIs invent package names, and attackers register exactly those names. Check the real name in the docs before installing.');
    const odd = pkgs.map((p, i) => found[i].young !== undefined ? `"${p.name}" was published ${found[i].young} day(s) ago`
      : found[i].few !== undefined ? `"${p.name}" had only ${found[i].few} downloads last week` : '').filter(Boolean);
    if (odd.length) return ask(ev, `Helena / packages: ${odd.join(', ')}. Make sure it is the package you mean, not a look-alike.`);
  }

  for (const [r, what] of DANGER) if (r.test(cmd))
    return ask(ev, `Helena / destructive: this command ${what}. It runs only if the user approves it now.`);
  for (const r of rules.ask) if (re(r) && re(r).test(cmd))
    return ask(ev, `Helena / team policy: commands matching "${r}" need the user's OK in this repo (.helena/policy).`);
  return null;
}

let input = '';
process.stdin.on('data', d => (input += d)).on('end', async () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  const out = await decide(ev);
  if (out) console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', ...out } }));
});
