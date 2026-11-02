// PostToolUse (Edit/Write/MultiEdit): agents run a check after only a small share of their edits, and a one-line reminder
// after editing raised the solve rate and cut output tokens (arXiv 2610.34577). After every 3rd code edit since the last
// test run, one line asks for the nearest test. Projects with no test command get nothing.
const { execSync } = require('child_process');
const { turn, CODE, TESTISH, testCommand } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);
const EVERY = 3;
const EDIT = ['Edit', 'Write', 'MultiEdit', 'NotebookEdit'];

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  const f = ev.tool_input && (ev.tool_input.file_path || ev.tool_input.notebook_path);
  if (!f || !CODE.test(f) || !ev.transcript_path) return;
  let edits = 0;
  try {
    for (const c of turn(ev.transcript_path).blocks) {
      if (c.type !== 'tool_use' || !c.input) continue;
      if (['Bash', 'PowerShell'].includes(c.name) && TESTISH.test(c.input.command || '')) break;
      if (EDIT.includes(c.name) && CODE.test(c.input.file_path || c.input.notebook_path || '')) edits++;
    }
  } catch { return; }
  if (!edits || edits % EVERY) return;
  let root = ev.cwd || process.cwd();
  try { root = execSync('git rev-parse --show-toplevel', { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500 }).trim(); } catch {}
  const cmd = testCommand(root);
  if (!cmd) return;
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PostToolUse',
    additionalContext: `Helena: ${edits} code edits since a test last ran. Run the test closest to what you changed before the next edit (the full suite is \`${cmd}\`).` } }));
});
