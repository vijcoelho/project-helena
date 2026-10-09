// Memory notes, read by start.js and router.js. Two places:
//   <vault>/Memory/*.md         yours, written by distill.py and /helena:remember
//   <repo>/.helena/memory/*.md  the team's: committed with the code, so a new note goes through code review
// A note can check itself (optional frontmatter, no LLM):
//   checks: src/cache.js, src/db.js#connectPostgres   files (or a name inside a file) the fact depends on
//   until: 2026-12-31                                 the fact stops holding after this date
// A failing check does not hide the note: it comes marked STALE with the reason, so the AI verifies before trusting it.
// supersedes: is handled when a note is written (distill.py moves the replaced note to <vault>/Archive).
const fs = require('fs'), path = require('path');
const { MEMORY } = require('./paths');

const field = (text, key) => ((text.match(new RegExp(`^${key}:\\s*(.+)$`, 'm')) || [])[1] || '').trim();

// '' when the note still holds, else why not
function stale(text, root) {
  const why = [], until = field(text, 'until');
  if (until && until < new Date().toISOString().slice(0, 10)) why.push(`expired on ${until}`);
  for (const c of root ? field(text, 'checks').split(',').map(s => s.trim()).filter(Boolean) : []) {
    const [file, name] = c.split('#');
    let st;
    try { st = fs.statSync(path.resolve(root, file)); } catch { why.push(`${file} no longer exists`); continue; }
    if (name && !(st.isFile() && fs.readFileSync(path.resolve(root, file), 'utf8').includes(name)))
      why.push(`${name} is no longer in ${file}`);
  }
  return why.join('; ');
}

// [{ file, slug, text, team, stale }] for the notes that apply in `cwd` (other projects' notes left out)
function notes(cwd) {
  const project = path.basename(cwd).toLowerCase(), out = [];
  for (const [dir, team] of [[MEMORY, false], [path.join(cwd, '.helena', 'memory'), true]]) {
    let files = [];
    try { files = fs.readdirSync(dir).filter(f => f.endsWith('.md')); } catch {}
    for (const f of files) {
      const text = fs.readFileSync(path.join(dir, f), 'utf8'), owner = field(text, 'project').toLowerCase();
      if (owner && owner !== project && !team) continue;
      // checks resolve against the project folder, so only notes that belong to this project run them
      out.push({ file: f, slug: f.slice(0, -3), text, team, stale: stale(text, team || owner ? cwd : '') });
    }
  }
  return out;
}

const mark = n => (n.team ? ' (team)' : '') + (n.stale ? `  [STALE: ${n.stale}. Check the code before relying on it, then fix or /helena:forget the note]` : '');

module.exports = { field, stale, notes, mark };
