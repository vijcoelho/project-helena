// Status line: how big this session's context is (re-read on every message) and which model is answering.
// Claude Code runs it after each message with the session JSON on stdin. start.js keeps a copy at ~/.helena/statusline.js.
const fs = require('fs');
let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev = {};
  try { ev = JSON.parse(input); } catch {}
  let ctx = 0;
  try {
    const fd = fs.openSync(ev.transcript_path, 'r'), size = fs.fstatSync(fd).size, n = Math.min(size, 256 * 1024);
    const buf = Buffer.alloc(n);
    fs.readSync(fd, buf, 0, n, size - n);
    fs.closeSync(fd);
    for (const line of buf.toString('utf8').split('\n').reverse()) {
      if (!line.includes('"usage"')) continue;
      try {
        const u = JSON.parse(line).message.usage;
        ctx = u.input_tokens + u.cache_creation_input_tokens + u.cache_read_input_tokens;
        break;
      } catch {}
    }
  } catch {}
  // the plan's usage limits come in this JSON (subscribers only); limits.js reads the copy to warn before they run out
  let lim = '';
  try {
    const r = ev.rate_limits;
    if (r) {
      fs.writeFileSync(require('path').join(require('os').homedir(), '.helena', 'limits-claude.json'), JSON.stringify(r));
      const pct = Math.round(Math.max(...Object.values(r).map(w => (w && w.used_percentage) || 0)));
      lim = ` · limit ${pct}%`;
    }
  } catch {}
  const k = Math.round(ctx / 1000);
  const tip = k >= 250 ? '  /clear?' : k >= 120 ? '  heavy' : '';
  const model = (ev.model && (ev.model.display_name || ev.model.id)) || '';
  process.stdout.write(`helena · ctx ${k}k${tip}${lim} · ${model}`);
});
