// Stop and SubagentStop: an AI saying "done" with failing tests is the most common way bad code gets through. When this
// turn (or this subagent) edited code, this runs the project's tests before it may finish; if they fail, the failure
// goes back to it to fix.
// Which tests: the first line of <repo>/.helena/test (a command, or "off"), else what the project has:
//   package.json "test" script → npm test   pytest config or tests/ → python -m pytest -q -x   Cargo.toml → cargo test   go.mod → go test ./...
//   tsconfig.json with typescript installed (and nothing above) → npx tsc --noEmit, so a turn that breaks types is sent back
// A suite slower than 4 minutes, or a test runner that is not installed, never blocks. Blocks once per turn at most.
const fs = require('fs'), path = require('path'), { spawnSync, execSync } = require('child_process');
const { audit, turnTools, TEST } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);
const CODE = /\.(js|jsx|ts|tsx|mjs|cjs|py|go|rs|java|kt|rb|php|cs|c|cc|cpp|h|swift|vue|svelte|astro)$/i;
const MISSING = /No module named pytest|command not found|is not recognized as|Missing script: "?test|ENOENT|not installed/i;
const TIMEOUT = 240e3;

function command(root) {
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
if (process.argv[2] === '--which') { console.log(command(path.resolve(process.argv[3] || '.'))); process.exit(0); }  // for the tests

// code files the AI edited since the user's last message
const editedThisTurn = transcript => [...new Set(turnTools(transcript)
  .filter(b => ['Edit', 'Write', 'MultiEdit', 'NotebookEdit'].includes(b.name) && b.input)
  .map(b => b.input.file_path || b.input.notebook_path).filter(f => f && CODE.test(f)))];

// differential check: the new/changed tests must fail once the code change is reverted, else they do not check it
const git = (root, args) => spawnSync('git', args, { cwd: root, encoding: 'utf8', timeout: 20e3, windowsHide: true });
const ID = ['-c', 'user.email=helena@local', '-c', 'user.name=helena'];  // stash needs an identity
function recover(root) {  // a killed hook may have left the code files in a stash: put them back first
  const l = git(root, ['stash', 'list']).stdout || '';
  const m = l.split('\n').find(x => x.includes('helena-differential'));
  if (!m) return null;
  return git(root, [...ID, 'stash', 'pop', m.split(':')[0]]).status === 0;  // only our entry: never the user's own stash
}
const stuck = 'Helena / differential check: your code changes could not be put back after the check; they are in `git stash` ' +
  'as "helena-differential". Run `git stash list` and `git stash pop <that entry>` before anything else.';
function differential(ev, root, cmd, run) {
  const lines = a => (git(root, a).stdout || '').split('\n').map(s => s.trim()).filter(Boolean);
  const diff = git(root, ['diff', '--name-only', 'HEAD']), others = git(root, ['ls-files', '--others', '--exclude-standard']);
  if (diff.status !== 0 || others.status !== 0) return;
  const all = [...new Set([...lines(['diff', '--name-only', 'HEAD']), ...lines(['ls-files', '--others', '--exclude-standard'])])]
    .filter(f => !f.startsWith('.helena/'));
  const tests = all.filter(f => TEST.test(f));
  const code = all.filter(f => !TEST.test(f) && !/\.(md|json|lock|toml|ya?ml|txt)$/i.test(f) && !path.basename(f).startsWith('.'));
  if (!tests.length || !code.length) return;
  const gd = git(root, ['rev-parse', '--git-dir']).stdout.trim();
  if (!gd) return;
  const mark = path.resolve(root, gd, 'helena-differential');
  const hash = require('crypto').createHash('sha1').update((git(root, ['diff', 'HEAD']).stdout || '') + '\0' + all.join('\n')).digest('hex');
  try { if (fs.readFileSync(mark, 'utf8').trim() === hash) return; } catch {}
  if (git(root, [...ID, 'stash', 'push', '-u', '-m', 'helena-differential', '--', ...code]).status !== 0) return;
  if (!(git(root, ['stash', 'list']).stdout || '').includes('helena-differential')) return;  // nothing was stashed
  let r, back;
  try { r = run(cmd); } finally { back = recover(root); }
  if (back === false) { audit({ ...ev, tool_input: { command: cmd } }, 'done', 'block', stuck); console.log(JSON.stringify({ decision: 'block', reason: stuck })); return; }
  if (r.error || r.status !== 0) { audit({ ...ev, tool_input: { command: cmd } }, 'done', 'allow', 'differential: tests fail without the change'); return; }
  try { fs.writeFileSync(mark, hash); } catch {}
  const why = `Helena / differential check: the new or changed tests (${tests.slice(0, 5).join(', ')}) pass even with your code change reverted, so they do not check it. ` +
    'Make one of them fail without the fix; or, if this is a pure refactor, say so and stop again.';
  audit({ ...ev, tool_input: { command: cmd } }, 'done', 'block', why);
  console.log(JSON.stringify({ decision: 'block', reason: why }));
}

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  // SubagentStop: a worker's edits are in its own transcript, not in the session's, and get the same check before it reports
  const transcript = ev.agent_transcript_path || ev.transcript_path;
  if (ev.stop_hook_active || !transcript) return;  // already blocked once this turn: no loop
  let edited = [];
  try { edited = editedThisTurn(transcript); } catch { return; }
  if (!edited.length) {  // no edits this turn: still put back code a killed check left stashed (fs probe first, git only if a stash exists)
    const c = ev.cwd || process.cwd();
    if (fs.existsSync(path.join(c, '.git', 'refs', 'stash')) && recover(c) === false) { audit(ev, 'done', 'block', stuck); console.log(JSON.stringify({ decision: 'block', reason: stuck })); }
    return;
  }
  let root = ev.cwd || process.cwd();
  try { root = execSync('git rev-parse --show-toplevel', { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500 }).trim(); } catch {}
  const run = c => spawnSync(c, { cwd: root, shell: true, encoding: 'utf8', timeout: TIMEOUT, env: { ...process.env, CI: '1', FORCE_COLOR: '0' }, windowsHide: true });
  const cmd = command(root);
  if (recover(root) === false) { audit(ev, 'done', 'block', stuck); console.log(JSON.stringify({ decision: 'block', reason: stuck })); return; }
  const r = cmd ? run(cmd) : { status: 0 };
  const output = `${r.stdout || ''}\n${r.stderr || ''}`.trim();
  if (r.error || r.status === null || MISSING.test(output)) return;
  if (r.status === 0) {
    // the human's hidden acceptance tests (.helena/holdout): the AI gets the names of the failing ones, never a message, a trace or a file
    const files = (() => { try { return fs.readdirSync(path.join(root, '.helena', 'holdout')); } catch { return []; } })();
    const hc = files.some(f => /^test_.*\.py$|_test\.py$/.test(f)) ? 'python -m pytest -q -rfE --tb=no --color=no -p no:cacheprovider .helena/holdout'
      : files.some(f => /\.test\.(js|mjs|cjs)$/.test(f)) ? 'node --test .helena/holdout' : '';
    if (hc) {
      const h = run(hc), ho = `${h.stdout || ''}\n${h.stderr || ''}`;
      if (h.error || h.status === null || MISSING.test(ho)) return;
      if (h.status !== 0) {
        const names = [...new Set([...ho.matchAll(/^(?:FAILED|ERROR) (\S+)|^\s*not ok \d+ - (.+)$/gm)].map(m => (m[1] || m[2]).trim()))].slice(0, 20);
        const why = 'hidden acceptance tests failed' + (names.length ? ': ' + names.join(', ') : '');
        audit({ ...ev, tool_input: { command: hc } }, 'done', 'block', why);
        console.log(JSON.stringify({ decision: 'block', reason: why }));
        return;
      }
    }
    if (cmd) differential(ev, root, cmd, run);
    return;
  }
  const why = `Helena / done check: you edited code this turn (${edited.map(f => path.basename(f)).slice(0, 5).join(', ')}) and \`${cmd}\` fails. ` +
    'Fix the code, not the test: do not weaken, skip or delete tests to make them pass. If this failure was already there ' +
    'before your change, say so to the user plainly instead of calling the work done.';
  audit({ ...ev, tool_input: { command: cmd } }, 'done', 'block', why);
  console.log(JSON.stringify({ decision: 'block', reason: why + '\n\n' + output.split('\n').slice(-60).join('\n') }));
});
