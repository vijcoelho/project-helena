// PreToolUse (Agent) + SubagentStop: keeps subagents from costing more than the work they do.
// Always on: a built-in worker started without a model does not run on the main one.
//     model: sonnet      a general-purpose worker started without a model runs on this one
//     search: haiku      same for the built-in Explore worker
// A pin never moves a worker to a model above the session's (on a Sonnet session nothing is pinned to Sonnet or Opus).
// Only with <repo>/.helena/delegate or ~/.helena/delegate (an empty file means these defaults), the caps:
//     parallel: 3        workers running at the same time
//     workers: 8         workers started for one request of yours (a retry loop stops here)
//     effort: medium     a pinned worker started without an effort runs on this one (no default: a CLI older than the
//                        Agent tool's `effort` field would refuse every worker)
// Always on too: a worker whose report passes 8000 characters is sent back once to put the full text in a file and
// report in 20 lines (`report: <characters>` changes the size, `report: off` stops it).
// `off` turns a line off (`model: off` and `search: off` in ~/.helena/delegate stop the pins everywhere). An agent type
// with its own model (a plugin's, yours in .claude/agents) is never repinned, and a call that names a model keeps it.
// A refused worker is told why, and the refusal lands in ~/.helena/audit.jsonl.
const fs = require('fs'), path = require('path'), { execSync } = require('child_process');
const { audit, lastCall, HOME } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);
const PINS = { model: 'sonnet', search: 'haiku' }, CAPS = { parallel: 3, workers: 8 };
const RANK = ['haiku', 'sonnet', 'opus', 'fable'], rank = m => RANK.findIndex(r => String(m).toLowerCase().includes(r));
const INHERITS = { 'general-purpose': 'model', claude: 'model', '': 'model', Explore: 'search' };  // built-ins that run on the main model
const REPORT = 8000;  // characters (~2k tokens) of a worker's last message before it is sent back once to shorten it
const STUCK = 30 * 60e3;  // a worker that never reported back (killed, refused by the user) stops counting after this

function config(cwd) {
  let root = cwd;
  try { root = execSync('git rev-parse --show-toplevel', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500 }).trim(); } catch {}
  for (const f of [path.join(root, '.helena', 'delegate'), path.join(HOME, 'delegate')]) {
    let text;
    try { text = fs.readFileSync(f, 'utf8'); } catch { continue; }
    const c = { ...PINS, ...CAPS, report: REPORT };
    for (const [, k, v] of text.matchAll(/^\s*(model|search|effort|parallel|workers|report)\s*:\s*([\w-]+)/gmi)) {
      const key = k.toLowerCase(), val = v.toLowerCase();
      if (val === 'off') c[key] = null;
      else if (key === 'model' || key === 'search') { if (rank(val) >= 0) c[key] = val; }
      else if (key === 'effort') { if (/^(low|medium|high|xhigh|max)$/.test(val)) c[key] = val; }
      else if (+val >= 1) c[key] = +val;
    }
    return c;
  }
  return { ...PINS, report: REPORT };  // no file: the pins and the report cap only
}

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  // one file per session: a `turn` line per request of the user (router.js), `start` per worker let through, `stop` per worker done
  const log = path.join(HOME, 'warnings', `${ev.session_id || 'x'}-workers`);
  const c = config(ev.cwd || process.cwd()), t = ev.tool_input || {};
  if (ev.hook_event_name === 'SubagentStop') {
    // A long report is paid once by the worker and then on every later message of the session that called it. Sent back
    // one time per worker: the full text goes in a file, the report says where. The slot stays taken while it rewrites.
    const said = String(ev.last_assistant_message || ''), flag = path.join(HOME, 'warnings', `${ev.session_id || 'x'}-report-${ev.agent_id || 'x'}`);
    if (c.report && said.length > c.report && !fs.existsSync(flag)) {
      try { fs.mkdirSync(path.dirname(flag), { recursive: true }); fs.writeFileSync(flag, ''); } catch {}
      const why = `Helena / delegate: your report is ${said.length} characters, and the session that called you re-reads all of it on every ` +
        'later message. Unless the caller asked for the full text: write the full version to a file' +
        (ev.scratchpad_dir ? ` under ${ev.scratchpad_dir.split(path.sep).join('/')}` : '') + ' and answer again in at most 20 lines: ' +
        'what you found or changed as `path:line`, the check you ran and its result, what is left, and that file\'s path.';
      audit({ ...ev, tool_input: { command: `${ev.agent_type || 'agent'}: report of ${said.length} characters` } }, 'delegate', 'block', why);
      return console.log(JSON.stringify({ decision: 'block', reason: why }));
    }
    if (fs.existsSync(log)) fs.appendFileSync(log, JSON.stringify({ t: 'stop' }) + '\n');
    return;
  }

  // Every call writes its line first and then replays the file up to it. The file order decides who gets through, so
  // parallel calls in one message agree on it without a lock, and a refused call takes no place.
  const id = ev.tool_use_id || String(Math.random()), live = [];
  let turn = 0, over = '';
  if (c.parallel || c.workers) {
    fs.mkdirSync(path.dirname(log), { recursive: true });
    fs.appendFileSync(log, JSON.stringify({ t: 'start', id, ts: Date.now() }) + '\n');
  }
  for (const line of c.parallel || c.workers ? fs.readFileSync(log, 'utf8').split('\n') : []) {
    let e;
    try { e = JSON.parse(line); } catch { continue; }
    if (e.t === 'turn') turn = 0;
    else if (e.t === 'stop') live.shift();
    else if (e.t === 'start') {
      while (live.length && e.ts - live[0] > STUCK) live.shift();
      over = c.workers && turn >= c.workers ? 'workers' : c.parallel && live.length >= c.parallel ? 'parallel' : '';
      if (e.id === id) break;
      if (!over) { live.push(e.ts); turn++; }
    }
  }
  if (over) {
    const why = over === 'workers'
      ? `Helena / delegate: ${turn} workers were already started for this request (.helena/delegate, workers: ${c.workers}). ` +
        'Do not start another: work with what they returned, do the rest here, or tell the user what is still missing and let them raise the number.'
      : `Helena / delegate: ${live.length} workers are running and ${c.parallel} is the most at a time here (.helena/delegate, parallel). ` +
        'Wait for one to report before starting this one, or do this part here.';
    audit({ ...ev, tool_input: { command: `${t.subagent_type || 'agent'}: ${t.description || ''}` } }, 'delegate', 'deny', why);
    return console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: why } }));
  }

  // the model that is answering now: a pin is a saving only below it. Unknown (no call yet in the transcript): pin.
  const main = rank(lastCall(ev.transcript_path).model), pin = c[INHERITS[t.subagent_type || '']];
  if (pin && !t.model && (main < 0 || rank(pin) < main))
    console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PreToolUse',
      updatedInput: { ...t, model: pin, ...(c.effort && !t.effort && { effort: c.effort }) } } }));
});
