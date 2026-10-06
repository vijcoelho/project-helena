// Stop: if the session touched front-end files, runs the contrast checker before letting Claude finish.
// Unreadable text comes back as a block and Claude fixes it. A rule in a skill gets ignored ("you didn't ask"); a hook does not.
// Static page: checks the .html on disk. App with a server (Next, Vite…): checks the localhost URLs that showed up
// in the session and still respond.
const fs = require('fs'), path = require('path'), { spawnSync } = require('child_process');
if (process.env.HELENA_DISTILLING) process.exit(0);
const FRONT = /\.(html?|css|scss|sass|less|tsx|jsx|vue|svelte|astro)$/i;
const MAX_URLS = 5;

let input = '';
process.stdin.on('data', d => (input += d)).on('end', async () => {
  let ev;
  try { ev = JSON.parse(input); } catch { return; }
  if (ev.stop_hook_active || !ev.transcript_path) return; // already blocked once: no loop

  const raw = fs.readFileSync(ev.transcript_path, 'utf8');
  const touched = new Set();
  for (const line of raw.split('\n')) {
    let d;
    try { d = JSON.parse(line); } catch { continue; }
    const c = d.message && d.message.content;
    if (d.type !== 'assistant' || !Array.isArray(c)) continue;
    for (const b of c) {
      const f = b.type === 'tool_use' && b.input && b.input.file_path;
      if (f && FRONT.test(f)) touched.add(path.resolve(ev.cwd || '.', f));
    }
  }
  if (!touched.size) return;

  const targets = new Set();
  for (const f of touched) {
    if (/\.html?$/i.test(f)) targets.add(f);
    else if (/\.css$/i.test(f) && fs.existsSync(path.dirname(f)))
      for (const h of fs.readdirSync(path.dirname(f))) if (/\.html?$/i.test(h)) targets.add(path.join(path.dirname(f), h));
  }
  // local server URLs mentioned in the session (command, log, reply), most recent first
  const urls = [...new Set((raw.match(/https?:\/\/(?:localhost|127\.0\.0\.1):\d{2,5}(?:\/[\w\-./]*)?/g) || [])
    .map(u => u.replace(/[.)\]]+$/, '')).reverse())];
  for (const u of urls) {
    if ([...targets].filter(a => a.startsWith('http')).length >= MAX_URLS) break;
    try {
      const r = await fetch(u, { signal: AbortSignal.timeout(2000) });
      if (r.ok && (r.headers.get('content-type') || '').includes('html')) targets.add(u);
    } catch {}
  }

  const problems = [];
  for (const t of targets) {
    if (!t.startsWith('http') && !fs.existsSync(t)) continue;
    const r = spawnSync('node', [path.join(__dirname, '..', 'tools', 'contrast.mjs'), t], { encoding: 'utf8', timeout: 90000 });
    if (r.status === 1) problems.push(`${t}\n${r.stdout.trim()}`);
  }
  if (!problems.length) return;
  console.log(JSON.stringify({
    decision: 'block',
    reason: 'Helena / readability: the page you touched has unreadable text (WCAG AA). Fix ALL of it, including outside ' +
      'what was asked: change only the color lightness and keep the palette. Then say in one line which texts you fixed.\n\n' +
      problems.join('\n\n'),
  }));
});
