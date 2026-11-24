// PostToolUse (Edit/Write/MultiEdit):
//  1. Fast syntax check (<150ms) on edited JS/MJS/CJS (`node --check`) and Python (`ast.parse`, writes zero __pycache__).
//     Silent when valid; surfaces syntax errors immediately so the AI does not stack more edits on broken syntax.
//  2. After every 3rd code edit since the last test run, one line asks for the nearest test (arXiv 2610.34577).
const fs = require('fs'), path = require('path'), { execSync, spawnSync } = require('child_process');
const { turn, CODE, TESTISH, testCommand } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);
const EVERY = 3;
const EDIT = ['Edit', 'Write', 'MultiEdit', 'NotebookEdit'];

function syntaxError(abs) {
  if (!fs.existsSync(abs)) return '';
  let r;
  if (/\.(js|mjs|cjs)$/i.test(abs)) {
    r = spawnSync(process.execPath, ['--check', abs], { encoding: 'utf8', timeout: 1500, windowsHide: true });
  } else if (/\.py$/i.test(abs)) {
    r = spawnSync('python', ['-c', 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read(),sys.argv[1])', abs],
      { encoding: 'utf8', timeout: 1500, windowsHide: true });
  } else return '';
  if (!r || r.error || r.status === 0) return '';
  return `${r.stderr || ''}\n${r.stdout || ''}`.trim().split(/\r?\n/).filter(Boolean).slice(0, 4).join('\n');
}

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  const f = ev.tool_input && (ev.tool_input.file_path || ev.tool_input.notebook_path);
  if (!f || !CODE.test(f)) return;
  const cwd = ev.cwd || process.cwd(), abs = path.resolve(cwd, f);
  const syn = syntaxError(abs);
  if (syn) {
    console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PostToolUse',
      additionalContext: `Helena / syntax check: ${path.basename(f)} has a syntax error right after your edit. Fix it before touching other files:\n${syn}` } }));
    return;
  }
  if (!ev.transcript_path) return;
  let edits = 0;
  try {
    for (const c of turn(ev.transcript_path).blocks) {
      if (c.type !== 'tool_use' || !c.input) continue;
      if (['Bash', 'PowerShell'].includes(c.name) && TESTISH.test(c.input.command || '')) break;
      if (EDIT.includes(c.name) && CODE.test(c.input.file_path || c.input.notebook_path || '')) edits++;
    }
  } catch { return; }
  if (!edits || edits % EVERY) return;
  let root = cwd;
  try { root = execSync('git rev-parse --show-toplevel', { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500 }).trim(); } catch {}
  const cmd = testCommand(root);
  if (!cmd) return;
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PostToolUse',
    additionalContext: `Helena: ${edits} code edits since a test last ran. Run the test closest to what you changed before the next edit (the full suite is \`${cmd}\`).` } }));
});
