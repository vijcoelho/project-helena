// Undo for any AI CLI: before each request, router.js snapshots the working tree (tracked + new files, .gitignore
// respected) as a commit kept in the reflog of refs/helena/turns. Your index, branch and stash are never touched.
//   node rewind.js          list the last snapshots
//   node rewind.js 1        put the folder back as it was before the last request (2 = the one before...)
// Rewinding snapshots the current state first, so `node rewind.js 1` again undoes the rewind.
// ponytail: one temp index per repo; two sessions snapshotting the same repo at the same instant could race on it
const fs = require('fs'), path = require('path'), { execSync } = require('child_process');
const REF = 'refs/helena/turns';

// snapshots are Helena's, not the user's commits: their own author, so a machine with no git identity works too
const WHO = { GIT_AUTHOR_NAME: 'helena', GIT_AUTHOR_EMAIL: 'helena@localhost', GIT_COMMITTER_NAME: 'helena', GIT_COMMITTER_EMAIL: 'helena@localhost' };
const git = (cwd, args, idx) => execSync(`git ${args}`, {
  cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 8000, maxBuffer: 64 << 20,
  env: { ...process.env, ...WHO, ...(idx ? { GIT_INDEX_FILE: idx } : {}) },
}).trim();

// tree of the working tree as it is now, built in a scratch index that starts as a copy of the real one (fast)
function tree(cwd) {
  const dir = git(cwd, 'rev-parse --absolute-git-dir'), idx = path.join(dir, 'helena-index');
  try { fs.copyFileSync(path.join(dir, 'index'), idx); } catch { try { fs.unlinkSync(idx); } catch {} }
  git(cwd, 'add -A', idx);
  return { tree: git(cwd, 'write-tree', idx), top: git(cwd, 'rev-parse --show-toplevel') };
}

const history = cwd => {
  try { return git(cwd, `reflog show --format=%H%x09%T%x09%cr%x09%gs ${REF}`).split('\n').filter(Boolean).map(l => l.split('\t')); }
  catch { return []; }
};

// saves a snapshot unless nothing changed since the last one; returns its commit or ''
function snapshot(cwd, label) {
  const { tree: t } = tree(cwd), last = history(cwd)[0];
  if (last && last[1] === t) return '';
  let parent = '';
  try { parent = ' -p ' + git(cwd, 'rev-parse HEAD'); } catch {}  // a repo with no commit yet has no HEAD
  const commit = git(cwd, `commit-tree ${t}${parent} -m helena-turn`);
  git(cwd, `update-ref --create-reflog -m "${label.replace(/["\r\n`$\\]/g, ' ').slice(0, 72)}" ${REF} ${commit}`);
  return commit;
}

// the distinct earlier states, newest first (the current one left out): what `rewind n` counts
function states(cwd, now = tree(cwd)) {
  const seen = new Set([now.tree]), out = [];
  for (const [commit, t, when, label] of history(cwd))
    if (!seen.has(t)) { seen.add(t); out.push({ commit, t, when, label }); }
  return out;
}

// puts back the n-th distinct state before the current one; returns what changed
function rewind(cwd, n = 1) {
  const now = tree(cwd), all = states(cwd, now), target = all[n - 1];
  if (!target) throw new Error(`no snapshot ${n} back (there are ${all.length})`);
  snapshot(cwd, 'before rewind');
  const dir = git(cwd, 'rev-parse --absolute-git-dir'), idx = path.join(dir, 'helena-index');
  git(now.top, `read-tree ${target.t}`, idx);
  git(now.top, 'checkout-index -a -f', idx);
  const added = git(now.top, `diff-tree -r --name-only --diff-filter=A ${target.t} ${now.tree}`).split('\n').filter(Boolean);
  for (const f of added) try { fs.unlinkSync(path.join(now.top, f)); } catch {}
  const changed = git(now.top, `diff-tree -r --name-only ${target.t} ${now.tree}`).split('\n').filter(Boolean);
  return { target, changed, removed: added };
}

module.exports = { snapshot, rewind, states };
if (require.main === module) {
  const cwd = process.cwd(), n = parseInt(process.argv[2], 10);
  try {
    if (n > 0) {
      const r = rewind(cwd, n);
      console.log(`Back to before "${r.target.label}" (${r.target.when}). ${r.changed.length} file(s) changed` +
        (r.removed.length ? `, removed: ${r.removed.join(', ')}` : '') + '.\nRun the same command again to undo this rewind.');
    } else {
      const list = states(cwd).slice(0, 15);
      console.log(list.length ? 'n  when             before the request\n' +
        list.map((x, i) => `${i + 1}  ${x.when.padEnd(16)} ${x.label}`).join('\n')
        : 'No snapshots yet: Helena takes one before each request in a git repo.');
    }
  } catch (e) { console.log('Helena / rewind: ' + (e.message.split('\n')[0] || 'not a git repository')); process.exitCode = 1; }
}
