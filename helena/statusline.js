// Status line: how big this session's context is (re-read on every message) and which model is answering.
// Claude Code runs it after each message with the session JSON on stdin. start.js keeps a copy at ~/.helena/statusline.js.
const fs = require('fs');
let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev = {};
  try { ev = JSON.parse(input); } catch {}
  // the last call: its context, the model that answered, when, and how long its cache lives (5 minutes or 1 hour).
  // Same reading as lastCall() in hooks/paths.js; this file runs alone from ~/.helena, so it keeps its own copy.
  let ctx = 0, said = '', at = 0, ttl = 0, found = false;
  try {
    const fd = fs.openSync(ev.transcript_path, 'r'), size = fs.fstatSync(fd).size, n = Math.min(size, 256 * 1024);
    const buf = Buffer.alloc(n);
    fs.readSync(fd, buf, 0, n, size - n);
    fs.closeSync(fd);
    for (const line of buf.toString('utf8').split('\n').reverse()) {
      if (!line.includes('"usage"')) continue;
      try {
        const d = JSON.parse(line), u = d.message.usage;
        if (/^</.test(d.message.model || '')) continue;  // "<synthetic>": an error written by the CLI, not a call
        if (!found) {
          found = true;
          ctx = (u.input_tokens || 0) + (u.cache_creation_input_tokens || 0) + (u.cache_read_input_tokens || 0);
          said = d.message.model || '';
          at = Date.parse(d.timestamp) || 0;
        }
        const c = u.cache_creation || {};
        ttl = c.ephemeral_1h_input_tokens ? 3600e3 : c.ephemeral_5m_input_tokens ? 300e3 : 0;
        if (ttl) break;
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
  const model = (ev.model && (ev.model.display_name || ev.model.id)) || '';
  // each model has its own cache: after a switch the next message reads the whole context at full price
  const family = s => (String(s).match(/haiku|sonnet|opus|fable/i) || [''])[0].toLowerCase();
  const now = family((ev.model && ev.model.id) || model), switched = now && family(said) && now !== family(said);
  const tip = switched && k >= 20 ? `  model changed: next message re-reads ${k}k uncached`
    : k >= 250 ? '  /clear?' : k >= 120 ? '  heavy' : '';
  // answer before this time and the context is read from the cache; after it, all of it is paid in full again
  const cache = !at || !ttl || k < 20 ? '' : Date.now() > at + ttl ? ' · cache expired'
    : ` · cache until ${new Date(at + ttl).toTimeString().slice(0, 5)}`;
  process.stdout.write(`helena · ctx ${k}k${tip}${cache}${lim} · ${model}`);
});
