// PostToolUse (Bash/PowerShell): what a command printed is re-read on every later message, and most of a long output is
// noise (progress lines, one passing test per line, a build log). trim.js works before the command runs and only knows
// a few commands; this works on the output itself, so it covers every command. No LLM.
//  1. over 4k characters: colour codes go, `\r` progress keeps its last state, a run of lines that differ only in their
//     numbers folds into first / "… N similar lines" / last
//  2. still over 20k: the first 40 and last 80 lines stay, and from the middle only the lines that look like a problem (error, failed, warning, traceback)
// Nothing is lost: the full output is saved in ~/.helena/out/ and the AI is told the path. The exit code is untouched.
// A command that prints content the AI asked to read (cat, head, sed, git diff, git show, anywhere in the command) is
// never touched: a folded file is a wrong file, and trim.js already refuses a dump that is too big before it runs.
// The output is only replaced when that cuts a quarter or more. Escape hatch: `# helena:full` in the command.
// ponytail: line heuristics, not a per-tool parser; a tool whose signal has none of the SIGNAL words loses its middle
// (the saved file is the way back). rtk knows each tool's format, and trim.js still hands the command to it first.
const fs = require('fs'), path = require('path');
const { HOME } = require('./paths');
const SOFT = 4000, HARD = 20e3, HEAD = 40, TAIL = 80, SIGNALS = 40, KEEP_DAYS = 3;
const SIGNAL = /\b(errors?|fail(ed|ure|ures|ing|s)?|fatal|panic(ked)?|exception|traceback|warn(ing|ings)?|denied|not found|cannot|unresolved|undefined)\b|^\s*(E|FAIL|ERR!|✗|✖|×)\s/i;
const CONTENT = /(^|&&|\|\||;|\||\bdo\s|\n)\s*(cat|type|Get-Content|gc|head|tail|sed|awk|jq|curl|git\s+(diff|show|blame))\b/i;

function fold(text) {
  const lines = text.replace(/\x1b\[[0-9;?]*[ -\/]*[@-~]/g, '').split(/\r?\n/).map(l => l.slice(l.lastIndexOf('\r') + 1));
  const out = [], key = l => l.replace(/\d+/g, '#').trim();
  for (let i = 0; i < lines.length;) {
    let j = i + 1;
    while (j < lines.length && key(lines[j]) === key(lines[i])) j++;
    if (j - i >= 4) out.push(lines[i], `… ${j - i - 2} similar lines`, lines[j - 1]);
    else out.push(...lines.slice(i, j));
    i = j;
  }
  return out;
}

// the text as the AI should see it; unchanged when it is short
function squeeze(text, hard = HARD) {
  if (text.length <= SOFT) return text;
  let lines = fold(text);
  if (lines.join('\n').length > hard && lines.length > HEAD + TAIL + 10) {
    const mid = lines.slice(HEAD, -TAIL), hits = [];
    mid.forEach((l, i) => { if (hits.length < SIGNALS && SIGNAL.test(l)) hits.push(`${HEAD + i + 1}: ${l}`); });
    lines = [...lines.slice(0, HEAD), `… ${mid.length} lines cut` + (hits.length ? `; the ones that look like a problem, with their line number:` : ''),
      ...hits, '…', ...lines.slice(-TAIL)];
  }
  return lines.map(l => l.length > 2000 ? l.slice(0, 2000) + ' …' : l).join('\n');  // one minified line can be the whole flood
}

if (require.main === module && !process.env.HELENA_DISTILLING) {
  let input = '';
  process.stdin.on('data', d => (input += d)).on('end', () => {
    let ev;
    try { ev = JSON.parse(input); } catch { return; }
    const r = ev.tool_response, cmd = (ev.tool_input && ev.tool_input.command) || '';
    if (!r || typeof r !== 'object' || r.isImage || /helena:full/.test(cmd) || CONTENT.test(cmd)) return;
    const so = String(r.stdout || ''), se = String(r.stderr || ''), before = so.length + se.length;
    if (before <= SOFT) return;
    const out = squeeze(so), err = squeeze(se), after = out.length + err.length;
    if (after > before * 0.75) return;
    let file = '';
    try {
      const dir = path.join(HOME, 'out');
      fs.mkdirSync(dir, { recursive: true });
      for (const f of fs.readdirSync(dir)) try { if (Date.now() - fs.statSync(path.join(dir, f)).mtimeMs > KEEP_DAYS * 86400e3) fs.unlinkSync(path.join(dir, f)); } catch {}
      file = path.join(dir, `${String(ev.session_id || 'x').slice(0, 8)}-${Date.now()}.log`);
      fs.writeFileSync(file, so + (se ? '\n--- stderr ---\n' + se : ''));
      fs.appendFileSync(path.join(HOME, 'trim.jsonl'), JSON.stringify({ session: ev.session_id || '', what: 'output: ' + cmd.replace(/\s+/g, ' ').slice(0, 40), tokens: Math.round((before - after) / 4) }) + '\n');
    } catch {}
    const note = `\n[Helena / context: ${after} of ${before} characters shown (repeated lines folded, long middle cut).` +
      (file ? ` Full output: ${file.split(path.sep).join('/')} - Grep it or Read it with offset/limit.` : '') + ' `# helena:full` in the command skips this.]';
    console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'PostToolUse', updatedToolOutput: { ...r, stdout: out + note, stderr: err } } }));
  });
}
module.exports = { squeeze, fold };
