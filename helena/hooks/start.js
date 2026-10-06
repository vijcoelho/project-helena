// SessionStart: puts in context, without anyone asking:
//  1. the folder's HANDOFF.md
//  2. a project brief built from git (structure, scripts, README line), so Claude doesn't re-explore the repo every session
//  3. the memory index, minus notes that belong to other projects
//  4. news from the background worker (a skill Helena created, plugins she turned off), to tell the user
// It also starts the worker when it is overdue (SessionEnd does not fire if the terminal is killed).
const fs = require('fs'), path = require('path'), { execSync, spawn } = require('child_process');
const { HOME, MEMORY } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);
const out = [], cwd = process.cwd(), project = path.basename(cwd);

// ONDE-PAREI.md: the creator's handoff name before v0.5, still read so older projects keep working
for (const name of ['HANDOFF.md', 'ONDE-PAREI.md']) {
  try {
    out.push(`There is a ${name} in this folder (handoff from the last session):\n\n` + fs.readFileSync(name, 'utf8') +
      `\nWhen you finish any item under "Next", update ${name}: move it to "Done" and write the next step.\n`);
    break;
  } catch {}
}

try {
  const git = a => execSync(`git ${a}`, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 1500, maxBuffer: 32 << 20 });
  const files = git('ls-files').split('\n').filter(Boolean);
  if (files.length && path.resolve(git('rev-parse --show-toplevel').trim()) === path.resolve(cwd)) {
    const count = (key, top) => Object.entries(files.reduce((m, f) => (m[key(f)] = (m[key(f)] || 0) + 1, m), {}))
      .sort((a, b) => b[1] - a[1]).slice(0, top);
    const dirs = count(f => f.includes('/') ? f.split('/')[0] + '/' : '.', 10).map(([d, n]) => `${d} ${n}`).join(', ');
    const exts = count(f => path.extname(f) || '(none)', 6).map(([e]) => e).join(' ');
    const lines = [`Project brief (${files.length} tracked files): ${dirs}. Main file types: ${exts}.`];
    try { lines.push('npm scripts: ' + Object.entries(JSON.parse(fs.readFileSync('package.json', 'utf8')).scripts || {}).map(([k, v]) => `${k}=\`${v}\``).join(', ')); } catch {}
    for (const f of ['pyproject.toml', 'requirements.txt', 'Cargo.toml', 'go.mod', 'docker-compose.yml', 'compose.yml', 'Dockerfile', 'Makefile'])
      if (files.includes(f)) lines.push(`has ${f}`);
    try {
      const readme = fs.readFileSync(files.find(f => /^readme\.md$/i.test(f)), 'utf8');
      lines.push('README: ' + readme.replace(/```[\s\S]*?```/g, '').split('\n').filter(l => l.trim() && !l.startsWith('#') && !l.startsWith('|'))[0].slice(0, 220));
    } catch {}
    lines.push('Last commits: ' + git('log --oneline -3').trim().split('\n').join(' | '));
    out.push(lines.join('\n') + '\nUse this before exploring; only open the files the request actually needs.');
  }
} catch {}

try {
  // ponytail: whole index every session; switch to retrieval only (router.js already injects matching notes) past ~150 notes
  const lines = fs.readdirSync(MEMORY).filter(f => f.endsWith('.md')).flatMap(f => {
    const text = fs.readFileSync(path.join(MEMORY, f), 'utf8');
    const owner = (text.match(/^project:\s*(.+)$/m) || [])[1];
    if (owner && owner.trim().toLowerCase() !== project.toLowerCase()) return [];
    return [`- ${f.slice(0, -3)}: ${(text.match(/^description:\s*(.+)$/m) || [])[1] || ''}`];
  });
  if (lines.length) out.push(
    `Helena's memory (${MEMORY.split(path.sep).join('/')}). Read the full note when it is relevant to the request:`,
    ...lines,
    'If the user corrects you or says something that holds from now on, create/update a note there: frontmatter `type` and ' +
    '`description` (plus `project: <folder>` when it only applies here), one fact per note, [[links]] to related notes, ' +
    'written in the language the user writes in.');
} catch {}

try {
  const news = JSON.parse(fs.readFileSync(path.join(HOME, 'news.json'), 'utf8'));
  if (news.length) {
    out.push('Helena news. Tell the user each item in one short line at the start of your first reply, keeping any command in it:\n- ' + news.join('\n- '));
    fs.writeFileSync(path.join(HOME, 'news.json'), '[]');
  }
} catch {}

try {  // keep a stable copy of the statusline script outside the versioned plugin folder
  const src = path.join(__dirname, '..', 'statusline.js'), dst = path.join(HOME, 'statusline.js');
  if (!fs.existsSync(dst) || fs.readFileSync(src, 'utf8') !== fs.readFileSync(dst, 'utf8')) fs.copyFileSync(src, dst);
} catch {}

let overdue = true;
try { overdue = Date.now() - fs.statSync(path.join(HOME, 'worker.last')).mtimeMs > 20 * 3600e3; } catch {}
if (overdue && !process.env.HELENA_EVAL) {
  fs.mkdirSync(HOME, { recursive: true });
  const fd = fs.openSync(path.join(HOME, 'worker.log'), 'a');
  spawn('python', [path.join(__dirname, '..', 'worker.py')], {
    detached: true, windowsHide: true, stdio: ['ignore', fd, fd],
    env: { ...process.env, HELENA_DISTILLING: '1', PYTHONIOENCODING: 'utf-8' },
  }).unref();
}

if (out.length) console.log(out.join('\n'));
