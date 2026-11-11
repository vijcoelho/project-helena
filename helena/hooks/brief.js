// SubagentStart: a worker starts cold. Whoever called it has to spend output tokens (the dearest kind, on the dearest
// model) telling it how the project is checked and what was already decided, or it guesses. This hands every worker, of
// any type, the same four things for free, before its first prompt:
//  1. how to report: short, path:line, the long version in a file (the caller re-reads the report on every later message)
//  2. the project's check command (the one done.js runs before the worker may finish)
//  3. `## Decisions` from HANDOFF.md, so it does not reopen what was settled or retry what was rejected
//  4. `tests: spec-only`, when the project has it
// No LLM. delegate.js sends back a report that comes out long anyway (SubagentStop).
const fs = require('fs'), path = require('path'), { execSync } = require('child_process');
const { testCommand, specOnly } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);
const DECISIONS = 1500;  // characters of the Decisions section a worker gets

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev = {};
  try { ev = JSON.parse(input); } catch {}
  const cwd = ev.cwd || process.cwd();
  let root = cwd;
  try { root = execSync('git rev-parse --show-toplevel', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500, windowsHide: true }).trim(); } catch {}
  const out = ['Helena, for this worker. Unless your own instructions set a report format: your caller reads only your last ' +
    'message and re-reads it on every message after, so make it at most 20 lines: what you found or changed as `path:line`, ' +
    'the check you ran and its result, what is left. No file contents, no recap of the steps. A result that needs more room ' +
    `goes in a file${ev.scratchpad_dir ? ` under ${ev.scratchpad_dir.split(path.sep).join('/')}` : ''} and you return its path with a 5-line summary.`];
  const cmd = testCommand(root);
  if (cmd) out.push(`This project's check is \`${cmd}\`. If you edit code, Helena runs it before you may finish: fix the code, never the test.`);
  if (specOnly(cwd)) out.push('Tests are spec-only here: write a test only when asked, or as a repro of the bug being fixed.');
  try {
    const text = fs.readFileSync(path.join(root, 'HANDOFF.md'), 'utf8'), m = text.match(/^##\s+Decisions\b[^\n]*\n([\s\S]*?)(?=^##\s|(?![\s\S]))/mi);
    const d = m && m[1].trim();
    if (d) out.push('Already settled (HANDOFF.md, Decisions). Do not reopen these or retry what they reject:\n' +
      (d.length > DECISIONS ? '…' + d.slice(-DECISIONS) : d));  // the newest decisions are at the end
  } catch {}
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'SubagentStart', additionalContext: out.join('\n') } }));
});
