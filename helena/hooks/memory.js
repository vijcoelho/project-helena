// Memory notes, read by start.js, router.js, gate.js and lifecycle.js. Two places:
//   <vault>/Memory/*.md         yours, written by distill.py and /helena:remember
//   <repo>/.helena/memory/*.md  the team's: committed with the code, so a new note goes through code review
// A note can check itself and bind to file paths (optional frontmatter, no LLM):
//   checks: src/cache.js, src/db.js#connectPostgres   files (or a name inside a file) the fact depends on
//   paths: helena/app/*, site/*.html                  globs that trigger this note when Read/Edit touches a match
//   until: 2026-12-31                                 the fact stops holding after this date
//   error_pattern: EBUSY.*unlink                      regex matched on PostToolUseFailure to inject a known fix
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

const normRel = p => String(p || '').replace(/\\/g, '/').replace(/^\.\//, '').replace(/\/+$/, '');

// simple glob -> RegExp supporting **, *, ? (case-insensitive on Windows)
function globMatch(pattern, rel) {
  const p = normRel(pattern), r = normRel(rel);
  if (!p || !r) return false;
  if (p === r) return true;
  if (!/[*?[]/.test(p)) return p.endsWith('/') ? r.startsWith(p) : r === p || r.startsWith(p + '/');
  const rx = p.replace(/[.+^${}()|\\]/g, '\\$&').replace(/\*\*\//g, '(?:.+/)?').replace(/\*\*/g, '.*')
    .replace(/\*/g, '[^/]*').replace(/\?/g, '[^/]');
  return new RegExp('^' + rx + '$', process.platform === 'win32' ? 'i' : '').test(r);
}

// file paths / globs a note binds to: explicit `paths:` plus the file portion of `checks:`
function pathsOf(text) {
  const fromPaths = field(text, 'paths').split(',').map(s => s.trim()).filter(Boolean);
  const fromChecks = field(text, 'checks').split(',').map(s => s.split('#')[0].trim()).filter(Boolean);
  return [...new Set([...fromPaths, ...fromChecks])];
}

// notes that apply to `filePath` when opened/edited inside `cwd`
function forFile(cwd, filePath) {
  if (!cwd || !filePath) return [];
  const abs = path.resolve(cwd, filePath), rel = normRel(path.relative(cwd, abs));
  if (!rel || rel.startsWith('..')) return [];
  return notes(cwd).filter(n => pathsOf(n.text).some(pat => globMatch(pat, rel)));
}

// Obsidian [[slug]] / [[slug|alias]] links in the note body, normalized to lowercase slugs
function linksOf(text) {
  const body = String(text || '').replace(/^---[\s\S]*?---\n/, '');
  return [...new Set([...body.matchAll(/\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]/g)]
    .map(m => m[1].trim().replace(/\.md$/i, '').toLowerCase()).filter(Boolean))];
}

const mark = n => (n.team ? ' (team)' : '') + (n.stale ? `  [STALE: ${n.stale}. Check the code before relying on it, then fix or /helena:forget the note]` : '');

module.exports = { field, stale, notes, mark, pathsOf, forFile, linksOf, globMatch };
