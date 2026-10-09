// Stop: an AI saying "done" with failing tests is the most common way bad code gets through. When this turn edited code,
// this runs the project's tests before Claude may finish; if they fail, the failure goes back to Claude to fix.
// Which tests: the first line of <repo>/.helena/test (a command, or "off"), else what the project has:
//   package.json "test" script → npm test   pytest config or tests/ → python -m pytest -q -x   Cargo.toml → cargo test   go.mod → go test ./...
// A suite slower than 4 minutes, or a test runner that is not installed, never blocks. Blocks once per turn at most.
const fs = require('fs'), path = require('path'), { spawnSync, execSync } = require('child_process');
const { audit, turnTools } = require('./paths');
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
  return '';
}

// code files the AI edited since the user's last message
const editedThisTurn = transcript => [...new Set(turnTools(transcript)
  .filter(b => ['Edit', 'Write', 'MultiEdit', 'NotebookEdit'].includes(b.name) && b.input)
  .map(b => b.input.file_path || b.input.notebook_path).filter(f => f && CODE.test(f)))];

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  if (ev.stop_hook_active || !ev.transcript_path) return;  // already blocked once this turn: no loop
  let edited = [];
  try { edited = editedThisTurn(ev.transcript_path); } catch { return; }
  if (!edited.length) return;
  let root = ev.cwd || process.cwd();
  try { root = execSync('git rev-parse --show-toplevel', { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500 }).trim(); } catch {}
  const cmd = command(root);
  if (!cmd) return;
  const r = spawnSync(cmd, { cwd: root, shell: true, encoding: 'utf8', timeout: TIMEOUT, env: { ...process.env, CI: '1', FORCE_COLOR: '0' }, windowsHide: true });
  const output = `${r.stdout || ''}\n${r.stderr || ''}`.trim();
  if (r.error || r.status === 0 || r.status === null || MISSING.test(output)) return;
  const why = `Helena / done check: you edited code this turn (${edited.map(f => path.basename(f)).slice(0, 5).join(', ')}) and \`${cmd}\` fails. ` +
    'Fix the code, not the test: do not weaken, skip or delete tests to make them pass. If this failure was already there ' +
    'before your change, say so to the user plainly instead of calling the work done.';
  audit({ ...ev, tool_input: { command: cmd } }, 'done', 'block', why);
  console.log(JSON.stringify({ decision: 'block', reason: why + '\n\n' + output.split('\n').slice(-60).join('\n') }));
});
