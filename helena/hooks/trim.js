// PreToolUse (Bash/PowerShell/Read): keeps junk out of the context, which is re-read on every message for the rest of
// the session. No LLM: regex + file size.
//  - a command that only needs a quieter flag gets the flag and runs (`git log` -> `git log --oneline -n 20`). Nothing is
//    refused, because a refusal costs one more model call and every call re-reads the whole context
//  - a command with no lean version that keeps its meaning (dumping a 200 KB log, a lockfile) is refused, with the lean way
// Escape hatch: a Bash command containing `helena:full`, or Read with an explicit `limit`.
// If rtk (github.com/rtk-ai/rtk) is on PATH, its `rtk rewrite` goes first: it knows many more commands than the table here.
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
if (process.env.HELENA_DISTILLING) process.exit(0);
const LOCK = /(^|[\\/])(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Cargo\.lock|composer\.lock|Gemfile\.lock|bun\.lockb?)$/i;
const BUILT = /([\\/](node_modules|dist|build|\.next|\.nuxt|out|coverage)[\\/])|\.min\.(js|css)$|\.map$/i;
const BIG = 100 * 1024; // ~25k tokens
const LIMITED = /-n\s*\d|-\d+\b|--max-count|--oneline|-1\b/;  // a git log that already says how much it wants
const LOUD = /\s-[a-zA-Z]*[qv]\b|--quiet|--verbose/;            // a command that already says how much it prints

// [a statement starts with, left alone when it already says, what goes in after the match, what the AI is told was cut,
//  also when piped]. Only flags are added: the exit code and the meaning of the command stay.
const LEAN = [
  [/^git\s+status\s*$/, null, ' -sb'],
  [/^git\s+log\b/, new RegExp(LIMITED.source + '|\\s-p\\b|--patch|--stat|--name-'), s => /--(pretty|format)/.test(s) ? ' -n 20' : ' --oneline -n 20',
    '`git log` ran with `-n 20`: the last 20 commits only. For more, say how many (`git log --oneline -n 100`); `git show <hash>` for one of them'],
  [/^grep\b/, (s, cwd) => !/\s-\w*r/i.test(s) || /--exclude-dir|--include/.test(s) || !fs.existsSync(path.join(cwd, 'node_modules')),
    ' --exclude-dir=node_modules --exclude-dir=.git', 'the recursive `grep` left node_modules and .git out (`# helena:full` searches them too)', true],
  // a traceback per failing test is most of what a test run prints: the short one goes in even when the AI asked for -v
  [/^(?:python\d?\s+-m\s+)?pytest\b/, s => LOUD.test(s) && /--tb/.test(s), s => (LOUD.test(s) ? '' : ' -q') + (/--tb/.test(s) ? '' : ' --tb=short')],
  [/^(?:python\d?\s+-m\s+)?pip\d?\s+install\b/, LOUD, ' -q'],
  [/^npm\s+(?:install|i|ci)\b/, /--loglevel|--silent|--verbose|--json|\s-(?:s|d|dd)\b/, ' --no-fund --loglevel=error'],
  [/^cargo\s+(?:build|test|check)\b/, LOUD, ' -q'],
];
const odd = (s, q) => (s.split(q).length - 1) % 2;  // an odd number of quotes before a point: the point is inside a string

// the command with the quiet flags in, and what was cut: { cmd, notes }, or null when nothing changes
function lean(cmd, cwd) {
  if (/<</.test(cmd)) return null;  // a heredoc's lines are text, not statements
  const notes = [];
  const out = cmd.replace(/(^|&&|\|\||;|\n)(\s*)([^;&|\n]+)/g, (all, sep, sp, stmt, at) => {
    const before = cmd.slice(0, at + sep.length), end = at + all.length;
    const piped = cmd[end] === '|' && cmd[end + 1] !== '|';
    if (odd(before, '"') || odd(before, "'") || />/.test(stmt)) return all;  // quoted text, or output that goes to a file
    for (const [start, skip, add, note, evenPiped] of LEAN) {
      const m = stmt.match(start);
      if (!m || (piped && !evenPiped) || (skip && (skip.test ? skip.test(stmt) : skip(stmt, cwd)))) continue;
      const head = m[0].trimEnd();
      if (note) notes.push(note);
      return sep + sp + head + (typeof add === 'function' ? add(stmt) : add) + stmt.slice(head.length);
    }
    return all;
  });
  return out === cmd ? null : { cmd: out, notes };
}

// `rtk rewrite <command>` prints the command with rtk in front of what it can shrink, and fails when it has nothing to do.
// No shell in between, and only a one-line answer that names rtk is taken: anything else is not run as a command.
function rtk(cmd) {
  const exe = (process.env.PATH || '').split(path.delimiter).filter(Boolean)
    .map(d => path.join(d, process.platform === 'win32' ? 'rtk.exe' : 'rtk')).find(f => fs.existsSync(f));
  if (!exe) return null;
  try {
    const out = execFileSync(exe, ['rewrite', cmd], { encoding: 'utf8', timeout: 2000, stdio: ['ignore', 'pipe', 'ignore'], windowsHide: true }).trim();
    return out !== cmd && /\brtk /.test(out) && !out.includes('\n') ? { cmd: out, notes: [] } : null;
  } catch { return null; }
}

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  const t = ev.tool_input || {}, cwd = ev.cwd || '.';
  const size = f => { try { return fs.statSync(path.resolve(cwd, f)).size; } catch { return 0; } };
  let why = '', what = '', tokens = 0, quiet = null;

  // Images cost by pixels, not bytes, and render checks (contact sheets in out/) need to be looked at.
  if (ev.tool_name === 'Read' && t.file_path && !t.limit && !/\.(png|jpe?g|gif|webp)$/i.test(t.file_path)) {
    what = path.basename(t.file_path); tokens = Math.round(size(t.file_path) / 4);
    if (LOCK.test(t.file_path)) why = 'lockfiles are huge and generated; read package.json, or Grep the lockfile for the one package you need';
    else if (BUILT.test(t.file_path)) why = 'this is generated/minified output; read the source file instead';
    else if (size(t.file_path) > BIG) why = `this file is ${Math.round(size(t.file_path) / 1024)} KB; Grep for what you need or Read with offset/limit`;
  } else if (t.command && !/helena:full/.test(t.command)) {
    let cmd = t.command;
    const piped = /\|\s*(head|tail|grep|rg|wc|Select-Object|Select-String|findstr|less|more)\b/i.test(cmd);
    const dumped = [...cmd.matchAll(/\b(?:cat|type|Get-Content|gc)\s+(?:-\w+\s+)*["']?([^\s|;&"']+)/gi)].map(m => m[1]);
    for (const f of dumped) {
      if (piped) break;
      if (LOCK.test(f)) why = `${f} is a lockfile; grep it for the one package you need`;
      else if (BUILT.test(f)) why = `${f} is generated output; read the source instead`;
      else if (size(f) > BIG) why = `${f} is ${Math.round(size(f) / 1024)} KB; use head/tail/grep or the Read tool with offset/limit`;
      if (why) { what = path.basename(f); tokens = Math.round(size(f) / 4); break; }
    }
    if (!why) {
      quiet = (ev.tool_name === 'Bash' && rtk(cmd)) || lean(cmd, cwd);
      if (quiet) cmd = quiet.cmd;
    }
    // what no flag makes lean (a history with every patch, a tree of node_modules) is still refused
    if (!why && /\bgit\s+log\b/.test(cmd) && !LIMITED.test(cmd) && !piped)
      why = 'git log without a limit prints the whole history; use `git log --oneline -20`';
    if (!why && /\b(grep|findstr)\b[^|;&]*\s-\w*r/i.test(cmd) && !/--exclude-dir|--include/.test(cmd) && fs.existsSync(path.join(cwd, 'node_modules')))
      why = 'recursive grep walks node_modules; use the Grep tool (it skips ignored files) or add --exclude-dir=node_modules';
    if (!why && /\b(ls\s+-\w*R|tree)\b/.test(cmd) && !piped && fs.existsSync(path.join(cwd, 'node_modules')))
      why = 'a recursive listing walks node_modules; use the Glob tool or `git ls-files`';
  }
  if (!why && quiet) {
    const told = quiet.notes.length ? `Helena / context: ${quiet.notes.join('. ')}.` : '';
    return console.log(JSON.stringify({ hookSpecificOutput: {
      hookEventName: 'PreToolUse', updatedInput: { ...t, command: quiet.cmd }, ...(told && { additionalContext: told }),
    } }));
  }
  if (!why) return;
  // the mod's band and /painel show what was kept out (tokens ~ bytes / 4; 0 when the size is unknown, e.g. git log)
  if (ev.session_id) try {
    const home = path.join(process.env.USERPROFILE || process.env.HOME || '.', '.helena');
    fs.mkdirSync(home, { recursive: true });
    fs.appendFileSync(path.join(home, 'trim.jsonl'), JSON.stringify({ session: ev.session_id, what: what || t.command.slice(0, 40), tokens }) + '\n');
  } catch {}
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse', permissionDecision: 'deny',
      permissionDecisionReason: `Helena / context: ${why}. Everything that enters the context is re-read on every message ` +
        'for the rest of the session. If you really need the full output, add the comment `# helena:full` to the command ' +
        '(or pass limit to Read).',
    },
  }));
});
