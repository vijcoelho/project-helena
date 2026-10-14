// PreToolUse (Bash/PowerShell): before `git commit` or `git push`, looks for API keys and .env files in what is about to go up.
// Found one → denies the command and says what. No LLM: regex + git, runs in milliseconds.
// Also enforces the project's git rules in .helena/git, which change from project to project:
//   main: no             direct commits on main/master are denied (merge and push stay free)
//   never: *.mp4 videos/ these paths never go into a commit (no slash matches the name in any folder, like .gitignore)
// The Portuguese spelling from v0.4 (`main: não`, `nunca:`) is still accepted.
const { execSync } = require('child_process');
const fs = require('fs'), path = require('path');
const { audit } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);

// same pattern as helena/distill.py (SECRET)
const SECRET = /\b(sk[_-][A-Za-z0-9_-]{16,}|[a-f0-9]{40,}|(pk|rk)_(live|test)_[A-Za-z0-9]{10,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|\d{8,}:[A-Za-z0-9_-]{30,}|(AKIA|ASIA)[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)/;
const ENV = /(^|\/)\.env(\.[\w-]+)?$/;
const ENV_OK = /\.env\.(example|sample|template)$/;

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  const cmd = (ev.tool_input && ev.tool_input.command) || '';
  const commit = /\bgit\b[^;&|]*\bcommit\b/.test(cmd), push = /\bgit\b[^;&|]*\bpush\b/.test(cmd);
  if (!commit && !push) return;

  const git = a => { try { return execSync(`git ${a}`, { cwd: ev.cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 64 << 20 }); } catch { return ''; } };
  const root = git('rev-parse --show-toplevel').trim();
  if (!root) return;

  // what goes in: what is already staged + what this same command's `git add` will add (it has not run yet)
  const adds = [...cmd.matchAll(/\bgit\s+add\s+([^;&|]+)/g)].map(m => m[1].trim().split(/\s+/));
  const all = adds.some(a => a.some(x => ['-A', '--all', '.', '*'].includes(x)));
  const tracked = all || adds.some(a => a.includes('-u')) || /\bcommit\b[^;&|]*\s-[a-z]*a[a-z]*\b/.test(cmd); // -u / commit -a: tracked files only
  const named = adds.flat().filter(x => !x.startsWith('-') && !['.', '*'].includes(x));
  const ignoringEnv = /\.env[^;&|]*>>?\s*\.gitignore/.test(cmd); // the command itself adds .env to .gitignore
  const files = new Set([
    ...git('diff --cached --name-only').split('\n'),
    ...(commit && tracked ? git('diff --name-only').split('\n') : []),
    ...(commit && all ? git('ls-files --others --exclude-standard').split('\n') : []),
    ...(commit ? named : []),
    ...(push ? git('diff --name-only @{u}..HEAD').split('\n') : []),
  ].filter(f => f && !(ignoringEnv && ENV.test(f))));

  const secrets = [];
  for (const f of files) {
    if (ENV.test(f) && !ENV_OK.test(f)) { secrets.push(`${f}: .env file (keep it out of git; add it to .gitignore)`); continue; }
    let text = '';
    try { text = fs.readFileSync(path.join(root, f), 'utf8'); } catch {}
    if (push && !text) text = git(`show HEAD:"${f}"`);
    const m = text.match(SECRET);
    if (m) secrets.push(`${f}: looks like a key/secret (${m[0].slice(0, 6)}…)`);
  }
  if (push) {
    const m = git('log -p --format= @{u}..HEAD').match(SECRET);  // no header: a commit hash is 40 hex chars too
    if (m && !secrets.length) secrets.push(`an unpushed commit contains a secret (${m[0].slice(0, 6)}…): rewrite that commit before pushing`);
  }

  // gitleaks, only if installed (v8): adds its findings on the staged changes. Missing, failing or slow = ignored. Prints file + rule, never the value.
  if (commit) {
    const exe = (process.env.PATH || '').split(path.delimiter).filter(Boolean).map(d => path.join(d, process.platform === 'win32' ? 'gitleaks.exe' : 'gitleaks')).find(p => fs.existsSync(p));
    // the report goes to a file outside the repo: every v8 writes one, and a stray report must never land in the commit
    const out = path.join(require('os').tmpdir(), `helena-gitleaks-${process.pid}.json`);
    if (exe) try {
      const r = require('child_process').spawnSync(exe, ['protect', '--staged', '--no-banner', '--redact', '--report-format', 'json', '--report-path', out],
        { cwd: root, timeout: 5000, stdio: 'ignore', windowsHide: true });
      if (!r.error && (r.status === 0 || r.status === 1))  // 1 = leaks found
        for (const x of JSON.parse(fs.readFileSync(out, 'utf8') || '[]')) secrets.push(`${x.File}: gitleaks rule ${x.RuleID}`);
    } catch {} finally { fs.rmSync(out, { force: true }); }
  }

  const broken = [];
  let rules = '';
  try { rules = fs.readFileSync(path.join(root, '.helena', 'git'), 'utf8'); } catch {}
  if (commit && /^main:\s*(no|n[aã]o)\b/mi.test(rules) && !/\bgit\s+(checkout|switch)\b/.test(cmd) &&
      ['main', 'master'].includes(git('rev-parse --abbrev-ref HEAD').trim()))
    broken.push('this project does not commit straight to main: create a branch (git switch -c <name>) and commit there');
  const never = ((rules.match(/^(never|nunca):(.*)$/mi) || [])[2] || '').trim().split(/\s+/).filter(Boolean).map(g => {
    const dir = g.endsWith('/'), body = g.replace(/\/$/, '');
    const re = body.replace(/^\//, '').replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[^/]*').replace(/\?/g, '[^/]');
    return new RegExp((body.includes('/') ? '^' : '(^|/)') + re + (dir ? '/' : '$'), 'i');
  });
  if (commit) for (const f of files) if (never.some(r => r.test(f))) broken.push(`${f}: stays out of commits in this project`);
  if (!secrets.length && !broken.length) return;

  const reason = [];
  if (secrets.length) reason.push('Helena / secrets: this would send a secret to git.\n- ' + secrets.join('\n- ') +
    '\nTake it out of the commit (git rm --cached / .gitignore), move the value to an environment variable and run again. ' +
    'If it is a false positive (e.g. a test hash), tell the user and ask them to confirm.');
  if (broken.length) reason.push('Helena / this project\'s git rules (.helena/git, agreed with the user):\n- ' + broken.join('\n- ') +
    '\nAdjust and run again (git restore --staged <file> takes it out of the commit). Only change .helena/git if the user asks.');
  audit(ev, 'guard', 'deny', reason.join(' '));
  console.log(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: reason.join('\n\n') },
  }));
});
