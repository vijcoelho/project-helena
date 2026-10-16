// PreToolUse: checks what the AI is about to do, before it happens. No LLM; the only network call is the package registry.
//  - secrets stay out of the context: reading a .env (Read, Grep, cat...) is denied and the reason lists its key names only
//  - new packages: `npm i x` / `pip install x` with a name that does not exist on the registry is denied (AIs invent
//    package names and attackers register them); one that is brand new or barely downloaded asks you first
//  - destructive commands (DROP TABLE, DELETE without WHERE, rm -rf /, git push --force, git reset --hard, a prod database
//    URL...) ask you first, even when permissions would have let them run
//    Also asked: a recursive delete of a variable that is unset or points at a root / home (`rm -rf "$X"/*`), a delete through
//    shutil.rmtree / fs.rmSync / rimraf / find -delete aimed at a root or home, and decoded text piped into a shell
//  - the audit trail: rm / truncate / `>` / Edit / Write on ~/.helena/*.jsonl, `git update-ref -d`, deleting refs/helena or
//    ~/.claude/projects/**/*.jsonl asks (the log of what the AI did must not be erasable by the AI); reading and `>>` are fine
//  - .env also counts when read through quote tricks (.e''nv), a glob that matches it, an interpreter one-liner, or cp / mv
//  - deleting a test file (rm, git rm, Remove-Item, del) asks
//  - a popular package installed with no version whose newest release is under 72 hours old asks, naming the previous version
//    (a hijacked maintainer account ships malware as a new release of a real package)
//  - tests: an edit that removes assertions from a test file or adds a skip asks you first (agents "fix" tests that way)
//  - the team's policy in <repo>/.helena/policy (versioned with the code):
//      deny: terraform apply        a regex per line; matching commands are denied
//      ask: kubectl                 matching commands ask first
//      mcp: github, helena          only these MCP servers may be used in this repo
//  - a curl / wget / Invoke-WebRequest leaves the hosts it names in ~/.helena/egress.jsonl (never blocks)
// Every decision lands in ~/.helena/audit.jsonl. Local hooks can be turned off by whoever owns the machine: this is a
// guardrail for the AI, not a sandbox.
const fs = require('fs'), os = require('os'), path = require('path'), { execSync } = require('child_process');
const { audit, egress, specOnly, TEST } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);

const ENV = /(^|[\\/])\.env(\.[\w-]+)?$/, ENV_OK = /\.env\.(example|sample|template)$/;
const ENV_IN_CMD = /\b(cat|type|Get-Content|gc|less|more|head|tail|bat|grep|rg|findstr|Select-String|sed|awk|strings|xxd)\b[^;&|]*?(?:^|[\s'"=])((?:[^\s'"=;|&]*[\\/])?\.env(?:\.[\w-]+)?)(?=$|[\s'";|&)])/i;
const ASSERT = /\bassert\w*\b|\bexpect\s*\(|\.should\b|\.to(Be|Equal|StrictEqual|Have|Throw|Match|Contain)\w*\s*\(/g;
const SKIP = /\b(it|test|describe)\.(skip|todo)\b|\bx(it|describe|test)\s*\(|@pytest\.mark\.(skip|xfail)|\bpytest\.skip\(|@unittest\.skip|\bt\.Skip\(|#\[ignore\]/g;
const NEW_TEST = /(^|[\\/])(test_[^\\/]+\.py|[^\\/]+_test\.py|[^\\/]+\.(test|spec)\.(js|ts|jsx|tsx|mjs|cjs)|[^\\/]+_test\.go)$/;
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

const READ = /\b(?:cat|type|Get-Content|gc|less|more|head|tail|bat|grep|rg|findstr|Select-String|sed|awk|strings|xxd)\b([^;&|]*)/i;
const COPY = /^\s*(?:sudo\s+)?(?:cp|mv|copy|copy-item|move|move-item)\s+(.*)$/i;
const VERB = /^\s*(?:sudo\s+|[({]\s*)*(rm|del|erase|ri|remove-item|git\s+rm|git\s+update-ref|cp|copy|copy-item|mv|move|truncate|unlink|shred|tee|rimraf|npx\s+rimraf|find)\s+(.*)$/i;
const unq = s => s.replace(/["']/g, '');
const SPLIT = /&&|\|\||;|\||\n/;

// a path with ~ / $HOME / %USERPROFILE% spelled out, forward slashes, lower case: comparable
const HOME = () => os.homedir().replace(/\\/g, '/').toLowerCase();
const norm = p => unq(p).replace(/^(~|\$\{?HOME\}?|%USERPROFILE%|\$env:(?:USERPROFILE|HOME))(?=$|[\\/])/i, os.homedir()).replace(/\\/g, '/').toLowerCase();
const rootish = p => { const n = norm(p).replace(/\/+$/, ''); return /^([~$%\\/]|[a-z]:)/i.test(unq(p)) && (n === '' || /^[a-z]:$/.test(n) || n === HOME()); };
// the audit trail: ~/.helena/*.jsonl, Claude's transcripts, git refs/helena
function trail(p, cwd) {
  const u = unq(p), n = norm(/^[~$%]/.test(u) || path.isAbsolute(u) ? u : path.resolve(cwd, u)), h = HOME();
  return /refs\/helena/.test(n) || (n === h + '/.helena' || n.startsWith(h + '/.helena/') || n.startsWith(h + '/.claude/projects/')) && /\.jsonl$|[*?]|\.helena\/?$/.test(n);
}
// a variable as the target of rm -rf: unset, a root or home, or followed by /.. or /*
function varBad(tok, cmd) {
  const m = unq(tok).match(/^(?:\$env:(\w+)|\$\{(\w+)\}|\$(\w+)|%(\w+)%)(.*)$/i);
  if (!m) return false;
  const name = m[1] || m[2] || m[3] || m[4], rest = m[5];
  let val = process.env[name];
  if (!val && /^(HOME|USERPROFILE)$/i.test(name)) val = os.homedir();
  if (/^[\\/]\.\.([\\/]|$)/.test(rest)) return true;
  // set earlier in this same command (`tmp=$(mktemp -d) && ... && rm -rf "$tmp"`): not unset, and its value is not ours to guess
  if (new RegExp(`(^|[\\s;&|(])(?:export\\s+)?\\$?${name}\\s*=(?!=)|\\bfor(each)?\\s*\\(?\\s*\\$?${name}\\s+in\\b`).test(cmd)) return false;
  if (!val || /^[\\/]\*/.test(rest)) return true;
  return !rest.replace(/[\\/]/g, '') && rootish(val);
}
// the simple commands we watch: { verb, flags, args }
const simple = cmd => cmd.split(SPLIT).map(s => s.match(VERB)).filter(Boolean).map(m => {
  const toks = m[2].trim().split(/\s+/).map(t => unq(t).replace(/[)}]+$/, '')).filter(Boolean);
  return { verb: m[1].toLowerCase().replace(/\s+/g, ' '), flags: toks.filter(t => /^-/.test(t)), args: toks.filter(t => !/^-/.test(t)) };
});
// risky things a person may still want: [why] for the first that fires
function risky(cmd, cwd) {
  for (const { verb, flags, args } of simple(cmd)) {
    const del = /^(rm|del|erase|ri|remove-item|git rm|unlink|shred)$/.test(verb);
    if ((verb === 'rm' ? flags.some(f => /^-[a-z]*r[a-z]*$/i.test(f) || f === '--recursive') : /^(ri|remove-item)$/.test(verb) && flags.some(f => /^-recurse$/i.test(f))) && args.some(a => varBad(a, cmd)))
      return 'recursively deletes a variable that is unset, points at a root or home folder, or is followed by /.. or /*';
    if (/rimraf$/.test(verb) && args.some(rootish) || verb === 'find' && flags.includes('-delete') && args.some(rootish))
      return 'deletes a root or home folder';
    const hit = /^(cp|copy|copy-item)$/.test(verb) ? args.slice(-1) : args;  // a copy only overwrites its last argument
    if ((del || /^(truncate|mv|move|cp|copy|copy-item)$/.test(verb) || verb === 'tee' && !flags.includes('-a')) && hit.some(a => trail(a, cwd)))
      return 'erases or overwrites the log of what the AI did, which must not be erasable by the AI';
    if (verb === 'git update-ref' && flags.some(f => /^(-d|--delete)$/.test(f)) && args.some(a => /refs\/helena/.test(a))) return 'erases the log of what the AI did (git update-ref -d), which must not be erasable by the AI';
    if (del && args.some(a => TEST.test(a) && !/__pycache__|\.pyc$/.test(a))) return 'deletes a test file';
  }
  for (const m of cmd.matchAll(/(?<!>)>(?![>&])\|?\s*(\S+)/g)) if (trail(m[1], cwd)) return 'overwrites the log of what the AI did, which must not be erasable by the AI';
  // a script that deletes a root or home (a quote may be backslash-escaped inside a one-liner)
  const q = '\\\\?[\'"]([^\'"\\\\]*)\\\\?[\'"]';
  for (const re of [new RegExp(`\\bshutil\\.rmtree\\(\\s*${q}`), new RegExp(`\\b(?:rmSync|rmdirSync|fs\\.rm)\\(\\s*${q}[^)]*recursive`)]) {
    const m = cmd.match(re);
    if (m && rootish(m[1])) return 'deletes a root or home folder';
  }
  if (/\bbase64\s+(?:-\w*d\w*|--decode)\b[^|;&]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b/.test(cmd) || /FromBase64String/i.test(cmd) && /\b(iex|Invoke-Expression)\b/i.test(cmd))
    return 'runs a command nobody can read (decoded text piped into a shell)';
  return null;
}

// .helena/holdout: the human's hidden acceptance tests, same rule as .env (any slash style, ../ and ./ folded, any case).
// A tool path may also be .helena itself or .helena/* (a recursive Grep / Glob would list or read the holdout)
const HOLD = /(^|\/)\.helena\/holdout(\/|$)/i, HOLD_WIDE = /(^|\/)\.helena(\/?$|\/\*)/i;
const holdNorm = p => path.posix.normalize(unq(String(p)).replace(/\\/g, '/'));
const holdPath = (p, wide) => !!p && (HOLD.test(holdNorm(p)) || !!wide && HOLD_WIDE.test(holdNorm(p)));
let holdFound = '';
const holdWhy = 'Helena / holdout: .helena/holdout holds the human\'s hidden acceptance tests; you cannot read, copy or edit them, and done runs them for you.';

// .env reached some way the plain rule misses: a glob that matches it, an interpreter one-liner, cp / mv of it
function envTok(t, cwd) {
  const h = holdNorm(t);
  if (HOLD.test(h)) return (holdFound = h);
  if (/[*?\[]/.test(t) && !/["']/.test(t) && /\//.test(h) && !/^[*?\[]/.test(h)) {  // a glob that can expand to the folder or a file in it
    const g = new RegExp('^' + h.replace(/[.+^${}()|\\]/g, '\\$&').replace(/\*+/g, '[^/]*').replace(/\?/g, '[^/]') + '$', 'i');
    if (['.helena/holdout', '.helena/holdout/a.py'].some(s => g.test(s))) return (holdFound = h);
  }
  if (!/[*?\[]/.test(t)) return ENV.test(unq(t)) && !ENV_OK.test(unq(t)) ? unq(t) : null;  // unq: .e''nv is .env
  if (/["']/.test(t)) return null;  // a quoted glob is not expanded by the shell
  const dir = path.dirname(t), base = path.basename(t);
  if (!base.startsWith('.') || !/\w/.test(base)) return null;
  try {
    const rx = new RegExp('^' + base.replace(/[.+^${}()|\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$');
    const f = fs.readdirSync(path.resolve(cwd, dir)).find(f => rx.test(f) && ENV.test(f) && !ENV_OK.test(f));
    return f && path.join(dir, f);
  } catch { return null; }
}
function envHit(cmd, cwd) {
  for (const s of cmd.split(SPLIT)) {
    const rd = s.match(READ), cp = s.match(COPY);
    if (rd) for (const t of rd[1].split(/\s+/)) { const f = envTok(t, cwd); if (f) return f; }
    if (cp) {
      // a copy that is still named .env (cp .env .env.backup), or goes into a folder, stays behind the same rule: let it be
      const all = cp[1].trim().split(/\s+/).filter(t => !/^-/.test(t)), to = unq(all[all.length - 1] || '');
      for (const t of all) { const f = envTok(t, cwd); if (f && HOLD.test(f)) return f; }  // the holdout never gets the "kept" pass
      const kept = ENV.test(to) || (() => { try { return fs.statSync(path.resolve(cwd, to)).isDirectory(); } catch { return /[\\/]$/.test(to); } })();
      if (!kept) for (const t of all.slice(0, -1)) { const f = envTok(t, cwd); if (f) return f; }
    }
  }
  const py = cmd.match(/\b(?:python3?|py|node|ruby|perl|php|deno)\b[^;&|]*?\s-[cepr]\b(.*)/);
  if (py) for (const m of py[1].matchAll(/(?:^|[\s'"(\/\\=])(\.env(?:\.[\w-]+)?)(?=$|[\s'")\\,\]}])/g)) if (!ENV_OK.test(m[1])) return m[1];
  if (py && /\.helena(?:[\\/]|\\\\)+holdout/i.test(unq(py[1]))) return (holdFound = '.helena/holdout');
  return null;
}

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
      if (/^(\d*|&)[<>]/.test(a)) { if (/[<>]$/.test(a)) i++; continue; }  // a redirect (2>&1, > out.txt) is not a package
      if (a.startsWith('-') || /[:\\]|^\.|^\/|^~/.test(a) || (a.includes('/') && !a.startsWith('@'))) continue;
      if (npm) out.push({ eco: 'npm', name: a.startsWith('@') ? a.split('@').slice(0, 2).join('@') : a.split('@')[0], pinned: /^@?[^@]+@(?!latest$)./.test(a) });
      else out.push({ eco: 'pypi', name: a.split(/[<>=!~\[;@ ]/)[0], pinned: /[<>=!~@]/.test(a) });
    }
  }
  return out.filter(p => p.name).slice(0, 6);
}

// { missing } / { young: days } / { few: weekly downloads } / { fresh: { version, hours, prev } } / {} (fine or unknown); never throws
// fresh = no version named and the newest release is under 72 h old: a hijacked maintainer account ships malware that way
async function registry({ eco, name, pinned }) {
  const get = async (url, accept) => { const r = await fetch(url, { signal: AbortSignal.timeout(3000), headers: accept ? { accept } : {} }); return { status: r.status, body: r.ok ? await r.json() : null }; };
  const hours = t => Math.round((Date.now() - t) / 36e5), num = (a, b) => a.localeCompare(b, undefined, { numeric: true });
  try {
    if (eco === 'npm') {
      // the search result carries the date of the newest version (a few KB; the full packument is megabytes); its name must be exact
      const [r, s] = await Promise.all([get(`https://api.npmjs.org/downloads/point/last-week/${name}`),
        pinned ? null : get(`https://registry.npmjs.org/-/v1/search?text=${encodeURIComponent(name)}&size=1`).catch(() => null)]);
      if (r.status === 404) return { missing: true };
      if (r.body && r.body.downloads < 200) return { few: r.body.downloads };
      const pk = s && s.body && s.body.objects && s.body.objects[0] && s.body.objects[0].package;
      if (pk && pk.name === name && hours(Date.parse(pk.date)) < 72) {
        const doc = (await get(`https://registry.npmjs.org/${name.replace('/', '%2f')}`, 'application/vnd.npm.install-v1+json')).body;  // names versions, no dates
        if (doc && doc['dist-tags'].latest === pk.version) {
          const prev = Object.keys(doc.versions).filter(v => /^\d+\.\d+\.\d+$/.test(v) && num(v, pk.version) < 0).sort(num).pop();
          return { fresh: { version: pk.version, hours: hours(Date.parse(pk.date)), prev } };
        }
      }
      return {};
    }
    const r = await get(`https://pypi.org/pypi/${encodeURIComponent(name)}/json`);
    if (r.status === 404) return { missing: true };
    const rel = (r.body && r.body.releases) || {};
    const at = v => Math.max(...(rel[v] || []).map(f => Date.parse(f.upload_time_iso_8601)).filter(Boolean));
    const first = Math.min(...Object.keys(rel).map(at).filter(isFinite)), days = isFinite(first) ? (Date.now() - first) / 864e5 : Infinity;
    if (days < 30) return { young: Math.round(days) };
    const latest = r.body && r.body.info && r.body.info.version;
    if (!pinned && latest && hours(at(latest)) < 72)
      return { fresh: { version: latest, hours: hours(at(latest)), prev: Object.keys(rel).filter(v => v !== latest && isFinite(at(v))).sort((a, b) => at(b) - at(a))[0] } };
    return {};
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

  if (['Read', 'NotebookRead'].includes(tool) && [t.file_path, t.notebook_path].some(p => holdPath(p))) return deny(ev, holdWhy);
  if (['Grep', 'Glob'].includes(tool) && [t.path, t.glob, t.pattern].some((p, i) => holdPath(p, true) && (i < 2 || tool === 'Glob'))) return deny(ev, holdWhy);
  if (['Edit', 'Write', 'MultiEdit'].includes(tool) && holdPath(t.file_path)) return ask(ev, holdWhy.replace('you cannot read, copy or edit them', 'you must not rewrite them'));
  if (tool === 'Read' && t.file_path && ENV.test(t.file_path) && !ENV_OK.test(t.file_path))
    return deny(ev, envWhy(t.file_path, envKeys(path.resolve(cwd, t.file_path))));
  if (tool === 'Grep' && [t.path, t.glob].some(p => p && ENV.test(p) && !ENV_OK.test(p)))
    return deny(ev, envWhy(t.path || t.glob, envKeys(path.resolve(cwd, t.path || '.env'))));

  if (['Edit', 'Write', 'MultiEdit'].includes(tool) && t.file_path && trail(t.file_path, cwd))
    return ask(ev, 'Helena / audit: this edit rewrites the log of what the AI did, which must not be erasable by the AI. Approve only if you meant it.');

  if (tool === 'Write' && t.file_path && NEW_TEST.test(t.file_path) && !fs.existsSync(path.resolve(cwd, t.file_path)) && specOnly(cwd))
    return ask(ev, 'Helena / tests: tests are spec-only here (tests: spec-only). Write this test only if the user asked for it or it reproduces the bug being fixed.');

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
  const envf = env && !ENV_OK.test(env[2]) ? env[2] : envHit(cmd, cwd);
  if (envf && envf === holdFound) return deny(ev, holdWhy);
  // any command naming the folder: a test runner pointed at it (pytest .helena/holdout) would print the assertions
  // (a heredoc body or a -m message is text, not a path: a commit message may name the folder)
  const bare = cmd.replace(/<<-?\s*['"]?(\w+)['"]?[^\n]*\n[\s\S]*?\n\s*\1\b/g, '').replace(/\s-m\s*("[^"]*"|'[^']*')/g, '');
  if (/\.helena[\\/]+holdout/i.test(unq(bare))) return deny(ev, holdWhy);
  if (envf) return deny(ev, envWhy(envf, envKeys(path.resolve(cwd, envf))));

  const rules = policy(cwd);
  for (const r of rules.deny) if (re(r) && re(r).test(cmd))
    return deny(ev, `Helena / team policy: this repo does not let AIs run commands matching "${r}" (.helena/policy). Ask the user to run it.`);

  // a command that sends or fetches over the network: the hosts it names go in the egress log
  if (/\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod|https?)\s/i.test(cmd))
    for (const h of new Set([...cmd.matchAll(/https?:\/\/([^\s\/'"`)]+)/g)].map(m => m[1]))) egress(ev, h);

  const pkgs = installs(cmd);
  if (pkgs.length) {
    const found = await Promise.all(pkgs.map(registry));
    const missing = pkgs.filter((p, i) => found[i].missing);
    if (missing.length)
      return deny(ev, `Helena / packages: ${missing.map(p => `"${p.name}" does not exist on ${p.eco === 'npm' ? 'npm' : 'PyPI'}`).join(', ')}. ` +
        'AIs invent package names, and attackers register exactly those names. Check the real name in the docs before installing.');
    const odd = pkgs.map((p, i) => found[i].young !== undefined ? `"${p.name}" was published ${found[i].young} day(s) ago`
      : found[i].few !== undefined ? `"${p.name}" had only ${found[i].few} downloads last week`
      : found[i].fresh ? `"${p.name}" ${found[i].fresh.version} came out ${found[i].fresh.hours} hour(s) ago` +
        (found[i].fresh.prev ? ` (the previous version was ${found[i].fresh.prev}: pin it with ${p.name}${p.eco === 'npm' ? '@' : '=='}${found[i].fresh.prev})` : '') : '').filter(Boolean);
    if (odd.length) return ask(ev, `Helena / packages: ${odd.join(', ')}. Make sure it is the package you mean, not a look-alike.`);
  }

  const why = [...DANGER.filter(([r]) => r.test(cmd)).map(d => d[1]), risky(cmd, cwd)].find(Boolean);
  if (why) return ask(ev, `Helena / destructive: this command ${why}. It runs only if the user approves it now.`);
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
