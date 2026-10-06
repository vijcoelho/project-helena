// PreToolUse (Bash/PowerShell/Read): stops commands that dump junk into the context, which then gets re-read on every
// message for the rest of the session. Suggests the lean version instead. No LLM: regex + file size.
// Escape hatch: a Bash command containing `helena:full`, or Read with an explicit `limit`.
const fs = require('fs'), path = require('path');
if (process.env.HELENA_DISTILLING) process.exit(0);
const LOCK = /(^|[\\/])(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Cargo\.lock|composer\.lock|Gemfile\.lock|bun\.lockb?)$/i;
const BUILT = /([\\/](node_modules|dist|build|\.next|\.nuxt|out|coverage)[\\/])|\.min\.(js|css)$|\.map$/i;
const BIG = 100 * 1024; // ~25k tokens

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  const t = ev.tool_input || {}, cwd = ev.cwd || '.';
  const size = f => { try { return fs.statSync(path.resolve(cwd, f)).size; } catch { return 0; } };
  let why = '', what = '', tokens = 0;

  if (ev.tool_name === 'Read' && t.file_path && !t.limit) {
    what = path.basename(t.file_path); tokens = Math.round(size(t.file_path) / 4);
    if (LOCK.test(t.file_path)) why = 'lockfiles are huge and generated; read package.json, or Grep the lockfile for the one package you need';
    else if (BUILT.test(t.file_path)) why = 'this is generated/minified output; read the source file instead';
    else if (size(t.file_path) > BIG) why = `this file is ${Math.round(size(t.file_path) / 1024)} KB; Grep for what you need or Read with offset/limit`;
  } else if (t.command && !/helena:full/.test(t.command)) {
    const cmd = t.command;
    const piped = /\|\s*(head|tail|grep|rg|wc|Select-Object|Select-String|findstr|less|more)\b/i.test(cmd);
    const dumped = [...cmd.matchAll(/\b(?:cat|type|Get-Content|gc)\s+(?:-\w+\s+)*["']?([^\s|;&"']+)/gi)].map(m => m[1]);
    for (const f of dumped) {
      if (piped) break;
      if (LOCK.test(f)) why = `${f} is a lockfile; grep it for the one package you need`;
      else if (BUILT.test(f)) why = `${f} is generated output; read the source instead`;
      else if (size(f) > BIG) why = `${f} is ${Math.round(size(f) / 1024)} KB; use head/tail/grep or the Read tool with offset/limit`;
      if (why) { what = path.basename(f); tokens = Math.round(size(f) / 4); break; }
    }
    if (!why && /\bgit\s+log\b/.test(cmd) && !/(-n\s*\d|-\d+\b|--max-count|--oneline|-1\b)/.test(cmd) && !piped)
      why = 'git log without a limit prints the whole history; use `git log --oneline -20`';
    if (!why && /\b(grep|findstr)\b[^|;&]*\s-\w*r/i.test(cmd) && !/--exclude-dir|--include/.test(cmd) && fs.existsSync(path.join(cwd, 'node_modules')))
      why = 'recursive grep walks node_modules; use the Grep tool (it skips ignored files) or add --exclude-dir=node_modules';
    if (!why && /\b(ls\s+-\w*R|tree)\b/.test(cmd) && !piped && fs.existsSync(path.join(cwd, 'node_modules')))
      why = 'a recursive listing walks node_modules; use the Glob tool or `git ls-files`';
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
