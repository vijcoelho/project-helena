// Lands the work of builders that ran in their own git worktrees (/helena:orchestrate waves, /helena:race) in this tree.
// One command where the orchestrator used to spend a model call per git step, each one re-reading its whole context.
//   node wave.js land <worktree> [<worktree> ...]
// For each worktree, in the order given: everything it changed against the commit it started from becomes one patch,
// the patch is checked against this tree and applied (nothing is staged or committed here), then the worktree and its
// branch are removed. A patch that does not apply is left alone: its worktree stays and the line says why, so two
// builders that touched the same lines never overwrite each other. One line per worktree, exit 1 if any did not land.
//   node wave.js --where     prints how to call this file (commands show it to the AI)
const { spawnSync } = require('child_process'), path = require('path');
const git = (cwd, args, input) => spawnSync('git', args, { cwd, input, encoding: 'utf8', maxBuffer: 256 << 20, windowsHide: true });

function land(here, wt) {
  if (git(wt, ['rev-parse', '--git-dir']).status !== 0) return [false, 'not a git worktree'];
  if (path.resolve(git(wt, ['rev-parse', '--show-toplevel']).stdout.trim()) === path.resolve(git(here, ['rev-parse', '--show-toplevel']).stdout.trim()))
    return [false, 'this is the main tree, not a worktree'];
  const branch = git(wt, ['rev-parse', '--abbrev-ref', 'HEAD']).stdout.trim();
  // the commit the worktree left this tree's history at: commits the builder made on top of it are part of the patch
  const base = git(wt, ['merge-base', 'HEAD', git(here, ['rev-parse', 'HEAD']).stdout.trim()]).stdout.trim() || 'HEAD';
  git(wt, ['add', '-A']);
  const patch = git(wt, ['diff', '--cached', '--binary', base]).stdout;
  if (!patch.trim()) return [true, 'no changes', branch];
  const check = git(here, ['apply', '--check', '--whitespace=nowarn', '-'], patch);
  if (check.status !== 0) return [false, (check.stderr || 'does not apply').trim().split('\n')[0] + ' (worktree kept)'];
  if (git(here, ['apply', '--whitespace=nowarn', '-'], patch).status !== 0) return [false, 'apply failed (worktree kept)'];
  const stat = git(wt, ['diff', '--cached', '--shortstat', base]).stdout.trim();
  return [true, stat, branch];
}

const [cmd, ...rest] = process.argv.slice(2);
if (cmd === '--where') console.log(`node "${__filename.split(path.sep).join('/')}" land <worktree> [<worktree> ...]`);
else if (cmd === 'land' && rest.length) {
  let bad = 0;
  for (const wt of rest) {
    const [ok, what, branch] = land(process.cwd(), wt);
    if (ok) {
      git(process.cwd(), ['worktree', 'remove', '--force', wt]);
      if (branch && branch !== 'HEAD') git(process.cwd(), ['branch', '-D', branch]);
    } else bad++;
    console.log(`${ok ? 'landed' : 'NOT LANDED'} ${wt}: ${what}`);
  }
  process.exit(bad ? 1 : 0);
} else { console.error('usage: node wave.js land <worktree> [<worktree> ...]'); process.exit(2); }
