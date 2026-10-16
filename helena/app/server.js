// The Helena app: one window that shows what Helena knows, checked and spent, read from the files the hooks already write.
// No service stays on: the window polls this server, and the server exits a minute and a half after the window closes.
//   node app/server.js            starts it in the background (or reuses the one running) and opens the window
//   node app/server.js --serve    the server itself, in the foreground
//   --port N (default: any free one), --no-open (no window; the tests use it)
// Only answers on 127.0.0.1, and only to a Host header naming it (a web page cannot reach it through DNS rebinding).
// The chat (POST /api/chat) runs the claude CLI you are logged into, so Helena's hooks run on it too. It needs the token
// written into the page: a custom header no other page can send without a preflight, which this server never answers.
const fs = require('fs'), path = require('path'), os = require('os'), http = require('http'), { spawn } = require('child_process');
const { HOME, MEMORY, lastCall } = require('../hooks/paths');
const { field, stale } = require('../hooks/memory');
const limits = require('../hooks/limits');
const PORTFILE = path.join(HOME, 'app.port'), IDLE = 90e3, DAY = 864e5;
const TOKEN = require('crypto').randomBytes(16).toString('hex');
const SAFE = /^[\w.-]{1,64}$/;  // model names and session ids go on a command line
let last = Date.now();
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };

// the JSON lines at the end of a file (the logs only grow; the app needs the recent part)
function tail(f, bytes = 256 * 1024) {
  try {
    const fd = fs.openSync(f, 'r'), size = fs.fstatSync(fd).size, n = Math.min(size, bytes), buf = Buffer.alloc(n);
    fs.readSync(fd, buf, 0, n, size - n);
    fs.closeSync(fd);
    const lines = buf.toString('utf8').split('\n');
    if (n < size) lines.shift();
    return lines.map(l => { try { return JSON.parse(l); } catch {} }).filter(Boolean);
  } catch { return []; }
}

// Claude Code sessions touched in the last 12 hours: where, which model, how big the context, the last thing asked
function sessions() {
  const root = path.join(os.homedir(), '.claude', 'projects'), out = [];
  let dirs = [];
  try { dirs = fs.readdirSync(root); } catch {}
  for (const d of dirs) {
    let files = [];
    try { files = fs.readdirSync(path.join(root, d)).filter(f => f.endsWith('.jsonl')); } catch {}
    for (const f of files) {
      const file = path.join(root, d, f), mtime = fs.statSync(file).mtimeMs;
      if (Date.now() - mtime < DAY / 2) out.push({ file, mtime, id: f.slice(0, -6) });
    }
  }
  return out.sort((a, b) => b.mtime - a.mtime).slice(0, 10).map(s => {
    const { ctx, model, at, ttl } = lastCall(s.file);
    let cwd = '', asked = '';
    for (const d of tail(s.file, 512 * 1024).reverse()) {
      cwd ||= d.cwd || '';
      const c = d.type === 'user' && d.message && d.message.content;
      // the user's own words: not a system reminder, a hook's note or a subagent's report sent in as a prompt
      const own = t => t && !/^\s*</.test(t) && !t.startsWith('Another Claude session');
      const text = typeof c === 'string' ? c : Array.isArray(c) ? (c.find(b => b.type === 'text' && own(b.text)) || {}).text : '';
      if (!asked && own(text)) asked = text.replace(/\s+/g, ' ').slice(0, 90);
      if (cwd && asked) break;
    }
    return { id: s.id, cwd, project: path.basename(cwd || s.id), model, ctx, at: at || s.mtime, cacheUntil: ttl && at ? at + ttl : 0, asked };
  }).filter(s => s.model && !path.resolve(s.cwd || '/').toLowerCase().startsWith(os.tmpdir().toLowerCase())).slice(0, 8);  // no call yet, or an eval sandbox
}

// every note in the vault: how many, which no longer hold (and why), which changed last
function memory(roots) {
  let files = [];
  try { files = fs.readdirSync(MEMORY).filter(f => f.endsWith('.md')); } catch {}
  const all = files.map(f => {
    const file = path.join(MEMORY, f), text = fs.readFileSync(file, 'utf8'), project = field(text, 'project').toLowerCase();
    return { file: f.slice(0, -3), description: field(text, 'description').replace(/^"|"$/g, ''), project,
      mtime: fs.statSync(file).mtimeMs, stale: stale(text, roots[project] || '') };
  });
  return { total: all.length, stale: all.filter(n => n.stale).map(({ file, stale }) => ({ file, stale })),
    recent: all.sort((a, b) => b.mtime - a.mtime).slice(0, 6).map(({ file, description, mtime }) => ({ file, description, mtime })) };
}

function state() {
  const list = sessions(), roots = {};
  for (const s of list) if (s.cwd) roots[path.basename(s.cwd).toLowerCase()] ||= s.cwd;
  const feed = [...tail(path.join(HOME, 'audit.jsonl')).map(r => ({ ...r, kind: r.decision })), ...tail(path.join(HOME, 'events.jsonl'))]
    .sort((a, b) => (a.ts < b.ts ? 1 : -1)).slice(0, 80);
  // the last done check of each session: passed, or sent back (and why)
  for (const s of list) {
    const r = feed.find(e => e.session === s.id && (e.kind === 'done' || (e.hook === 'done' && e.decision === 'block')));
    s.check = r ? { ok: r.kind === 'done', cmd: r.cmd ?? r.what, why: r.why || '', ts: r.ts } : null;
  }
  const iso = t => new Date(t - new Date().getTimezoneOffset() * 6e4).toISOString().slice(0, 19);  // logs use local time
  const today = iso(Date.now()).slice(0, 10), week = iso(Date.now() - 7 * DAY);
  const ledger = tail(path.join(HOME, 'ledger.jsonl'));
  const sum = since => ledger.filter(r => r.ts >= since).reduce((a, r) => a + (r.cost || 0), 0);
  const hosts = {};
  for (const r of tail(path.join(HOME, 'egress.jsonl'))) if (r.ts >= week) hosts[r.to] = (hosts[r.to] || 0) + 1;
  return {
    now: Date.now(), here: arg('--here', process.cwd()), ais: available(), commands: commands(), models: modelList,
    limits: limits.all().map(a => ({ name: a.name, pct: a.pct, windows: a.windows || [], pace: limits.pace(a.windows) })),
    sessions: list, feed, memory: memory(roots),
    cost: { today: sum(today), week: sum(week) },
    egress: Object.entries(hosts).sort((a, b) => b[1] - a[1]).slice(0, 6),
  };
}

function open(url) {
  if (process.argv.includes('--no-open')) return;
  const run = (cmd, args) => spawn(cmd, args, { detached: true, stdio: 'ignore', windowsHide: true }).unref();
  // Windows: Helena's own frameless window (shell.js), or an Edge app window if it cannot be built;
  // ponytail: elsewhere the default browser, in a normal tab
  if (process.platform === 'win32') return require('./shell').ensure().then(exe => exe ? run(exe, [url])
    : run('cmd', ['/c', 'start', '', 'msedge', `--app=${url}`, '--window-size=1280,860']));
  run(process.platform === 'darwin' ? 'open' : 'xdg-open', [url]);
}

const brief = i => String(i.command || i.file_path || i.AbsolutePath || i.pattern || i.description || i.url || i.prompt || JSON.stringify(i)).replace(/\s+/g, ' ').slice(0, 140);
const tryJSON = v => { try { return JSON.parse(v); } catch { return undefined; } };
// the first line of a file, read in small pieces: a codex log opens with a long session line
function firstLine(f) {
  const fd = fs.openSync(f, 'r'), chunk = Buffer.alloc(65536), parts = [];
  try {
    for (let pos = 0; pos < 4 << 20;) {
      const n = fs.readSync(fd, chunk, 0, chunk.length, pos);
      if (!n) break;
      const i = chunk.subarray(0, n).indexOf(10);
      if (i >= 0) { parts.push(Buffer.from(chunk.subarray(0, i))); break; }
      parts.push(Buffer.from(chunk.subarray(0, n))); pos += n;
    }
  } finally { fs.closeSync(fd); }
  return Buffer.concat(parts).toString('utf8');
}
// follow a log another process writes: every new JSON line goes to fn
function follow(file, fn) {
  let pos = 0, rest = '';
  const t = setInterval(() => {
    try {
      const size = fs.statSync(file).size;
      if (size <= pos) return;
      const fd = fs.openSync(file, 'r'), buf = Buffer.alloc(size - pos);
      fs.readSync(fd, buf, 0, buf.length, pos); fs.closeSync(fd); pos = size;
      const lines = (rest + buf.toString('utf8')).split('\n');
      rest = lines.pop();
      for (const l of lines) { const d = tryJSON(l); if (d) fn(d); }
    } catch {}
  }, 700);
  return () => clearInterval(t);
}
const text = c => typeof c === 'string' ? c : Array.isArray(c) ? c.map(b => b.text || '').join(' ') : '';

// one claude stream-json line -> the few things the window shows. A subagent's own tool calls come tagged with the call
// that started it (sub), so the window can draw each one live under its card instead of a "waiting…" stub.
function relayClaude(d, send, run) {
  const agents = run.agents;
  const sub = d.parent_tool_use_id || undefined;
  if (d.type === 'system' && d.subtype === 'init') { if (!sub) send({ t: 'id', id: d.session_id, model: d.model }); }
  else if (d.type === 'stream_event') { if (!sub && d.event.delta && d.event.delta.type === 'text_delta') send({ t: 'text', s: d.event.delta.text }); }
  else if (d.type === 'assistant') {
    for (const b of d.message.content || []) {
      if (b.type !== 'tool_use') continue;
      const i = b.input || {}, agent = (b.name === 'Task' || b.name === 'Agent') ? (i.subagent_type || 'general-purpose') : '';
      if (agent) agents.add(b.id);
      send({ t: 'tool', id: b.id, sub, name: b.name, s: agent ? String(i.description || '') : brief(i), agent, model: i.model || '' });
    }
  } else if (d.type === 'user') {
    // a background subagent finished: its notice comes in as a user turn naming the call that started it
    const n = !sub && /<task-notification>[\s\S]*?<tool-use-id>([^<]+)<\/tool-use-id>[\s\S]*?<status>([^<]+)</.exec(text(d.message && d.message.content));
    if (n) {
      const s = text(d.message.content), num = k => +((new RegExp(`<${k}>(\\d+)`).exec(s) || [])[1] || 0);
      return send({ t: 'agentdone', id: n[1], ok: n[2] === 'completed', tokens: num('subagent_tokens'), ms: num('duration_ms') });
    }
    if (!Array.isArray(d.message && d.message.content)) return;
    // errors always (that is where Helena's blocks show), and what a subagent hands back
    for (const b of d.message.content) if (b.type === 'tool_result' && (b.is_error || agents.has(b.tool_use_id)))
      // a subagent's report comes wrapped in the harness's own notice: the window shows the report
      send({ t: 'res', id: b.tool_use_id, sub, err: !!b.is_error, s: text(b.content).replace(/^[\s\S]*?The report follows:/, '').replace(/\s+/g, ' ').trim().slice(0, 400) });
  } else if (d.type === 'result' && !sub) send({ t: 'end', cost: d.total_cost_usd || 0, error: d.is_error ? String(d.result || 'erro') : '' });
}

// codex exec --json: a thread, then items (commands, MCP calls, file changes, the answer) and the turn's end.
// Its subagents never show in that stream: each is a thread of its own, logged in ~/.codex/sessions with the
// parent's id, so the window follows those logs.
function relayCodex(d, send, run) {
  const it = d.item || {};
  if (d.type === 'thread.started') { send({ t: 'id', id: d.thread_id, model: 'codex' }); run.main = d.thread_id; codexKids(run, send); }
  else if (d.type === 'item.started' && it.type === 'command_execution') send({ t: 'tool', id: it.id, name: 'Bash', s: brief(it) });
  else if (d.type === 'item.started' && it.type === 'mcp_tool_call') send({ t: 'tool', id: it.id, name: `${it.server}.${it.tool}`, s: brief(it.arguments || {}) });
  else if (d.type === 'item.completed') {
    if (it.type === 'agent_message') send({ t: 'text', s: it.text + '\n' });
    else if (it.type === 'file_change') send({ t: 'tool', id: it.id, name: 'Edit', s: (it.changes || []).map(c => c.path).join(', ').slice(0, 140) });
    else if (it.type === 'command_execution' && it.exit_code) send({ t: 'res', id: it.id, err: true, s: `exit ${it.exit_code}: ${String(it.aggregated_output || '').trim().split('\n').pop()}`.slice(0, 400) });
    else if (it.type === 'mcp_tool_call' && it.error) send({ t: 'res', id: it.id, err: true, s: String(it.error.message || it.error).slice(0, 400) });
  } else if (d.type === 'turn.completed') send({ t: 'end', cost: 0, tokens: (d.usage || {}).output_tokens || 0, error: '' });
  else if (d.type === 'turn.failed' || d.type === 'error') send({ t: 'end', cost: 0, error: String((d.error && d.error.message) || d.message || 'erro') });
}

function codexKids(run, send) {
  const t0 = Date.now(), seen = new Set();
  const day = () => { const n = new Date(); return path.join(os.homedir(), '.codex', 'sessions', `${n.getFullYear()}`, `${n.getMonth() + 1}`.padStart(2, '0'), `${n.getDate()}`.padStart(2, '0')); };
  // a codex step: the shell command inside its exec script, or the tool's arguments; its reply to the parent is encrypted
  const cmd = c => {
    if (c.name === 'send_message') return 'devolvendo ao principal';
    const m = /cmd:\s*"((?:[^"\\]|\\.)*)"/.exec(c.input || '');
    return m ? m[1].replace(/\\"/g, '"') : tryJSON(c.arguments) ? brief(tryJSON(c.arguments)) : String(c.input || '');
  };
  const scan = setInterval(() => {
    let files = [];
    try { files = fs.readdirSync(day()).filter(f => f.endsWith('.jsonl')).map(f => path.join(day(), f)); } catch {}
    for (const f of files) {
      if (seen.has(f)) continue;
      try { if (fs.statSync(f).mtimeMs < t0 - 5000) { seen.add(f); continue; } } catch { continue; }
      const meta = (tryJSON(firstLine(f)) || {}).payload;
      if (!meta) continue;  // still being written
      seen.add(f);
      if (!meta.parent_thread_id || (meta.parent_thread_id !== run.main && !run.kids.has(meta.parent_thread_id))) continue;
      const nested = meta.parent_thread_id !== run.main;
      send({ t: 'tool', id: meta.id, sub: nested ? meta.parent_thread_id : undefined, name: 'Agent', model: 'codex',
        agent: [meta.agent_role || 'subagente', meta.agent_nickname].filter(Boolean).join(' '), s: String(meta.agent_path || '').split('/').pop().replace(/_/g, ' ') });
      run.watch(meta.id, f, d => {
        const x = d.payload || {};
        if (d.type === 'response_item' && (x.type === 'custom_tool_call' || x.type === 'function_call'))
          send({ t: 'tool', id: x.call_id, sub: meta.id, name: x.name === 'exec' ? 'Bash' : x.name, s: cmd(x).replace(/\s+/g, ' ').slice(0, 140) });
        if (d.type === 'event_msg' && x.type === 'task_complete') return { ok: true, s: String(x.last_agent_message || '') };
      });
    }
  }, 1000);
  run.stops.push(() => clearInterval(scan));
}

// agy (Antigravity, the Gemini models) -p --output-format stream-json: an init, then steps. A subagent only shows as
// the step that started it; its own steps go to a transcript (log_uri), which the window follows.
function relayAgy(d, send, run) {
  const s = d.step_update;
  if (d.event === 'init') send({ t: 'id', id: d.conversation_id, model: 'antigravity' });
  else if (s && s.step_type === 'subagent') {
    if (s.state !== 'DONE' || !s.subagent_info) return;
    for (const a of s.subagent_info.subagents || []) {
      if (!a.conversation_id || run.kids.has(a.conversation_id)) continue;
      send({ t: 'tool', id: a.conversation_id, name: 'Agent', model: 'gemini', agent: a.role || a.type_name || 'subagente', s: String(a.initial_prompt || '').replace(/\s+/g, ' ').slice(0, 140) });
      let file = '';
      try { file = require('url').fileURLToPath(a.log_uri); } catch {}
      if (!file) continue;
      let said = '';  // what it sends back to the caller (send_message), better than its last line
      run.watch(a.conversation_id, file, st => {
        for (const c of st.tool_calls || []) {
          const args = Object.fromEntries(Object.entries(c.args || {}).map(([k, v]) => [k, tryJSON(v) ?? v]));
          if (c.name === 'send_message') said = Object.values(args).filter(v => typeof v === 'string').sort((x, y) => y.length - x.length)[0] || said;
          send({ t: 'tool', id: `${a.conversation_id}:${st.step_index}:${c.name}`, sub: a.conversation_id, name: c.name, s: args.toolAction || brief(args) });
        }
        if (st.status === 'ERROR') send({ t: 'res', id: `${a.conversation_id}:${st.step_index}`, sub: a.conversation_id, err: true, s: String(st.error || 'erro').slice(0, 300) });
        if (st.type === 'PLANNER_RESPONSE' && st.status === 'DONE' && !(st.tool_calls || []).length && st.content) return { ok: true, s: said || String(st.content) };
      });
    }
  }
  else if (s && s.step_type === 'agent_response' && s.text_delta) send({ t: 'text', s: s.text_delta });
  else if (s && s.step_type === 'tool' && s.state === 'ACTIVE') send({ t: 'tool', id: `${s.step_index}`, name: s.tool_name, s: brief((s.tool_info || {}).parameters || {}) });
  else if (s && /ERROR|FAIL/.test(s.state || '')) send({ t: 'res', id: `${s.step_index}`, err: true, s: String(s.error || s.state).slice(0, 400) });
}

// the AIs the chat can run: each one's CLI as you are logged into it. The prompt goes on stdin where the CLI takes it;
// agy is a real .exe, so its prompt goes as an argument with no shell in between.
const WIN = process.platform === 'win32';
const AIS = {
  claude: { cmd: 'claude', shell: WIN, relay: relayClaude, stdin: true, args: (m, s, fork, text, e) => ['-p', '--output-format', 'stream-json', '--verbose',
    '--include-partial-messages', '--permission-mode', 'acceptEdits', ...(m ? ['--model', m] : []), ...(e ? ['--effort', e] : []), ...(s ? ['--resume', s, ...(fork ? ['--fork-session'] : [])] : [])] },
  // exec never asks, so without the -c Helena's own MCP tools (memory, context) are refused as "requires approval"
  codex: { cmd: 'codex', shell: WIN, relay: relayCodex, stdin: true, args: (m, s, fork, text, e) => ['exec', '--json', '--skip-git-repo-check', '-s', 'workspace-write',
    '-c', 'mcp_servers.helena.default_tools_approval_mode=approve',
    ...(m ? ['-m', m] : []), ...(e ? ['-c', `model_reasoning_effort=${e}`] : []), ...(s ? ['resume', s] : []), '-'] },
  agy: { cmd: 'agy', shell: false, relay: relayAgy, stdin: false, args: (m, s, fork, text, e) => ['-p', text, '--output-format', 'stream-json',
    '--mode', 'accept-edits', ...(m ? ['--model', m] : []), ...(e ? ['--effort', e] : []), ...(s ? ['--conversation', s] : [])] },
};
// each AI's models, as its own CLI lists them (its /model), with the reasoning efforts each takes.
const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max'];
// claude has no list command until the catalog is read: its aliases always point at the latest of each family
// the page writes each hint in its own language from these fields: ctx (tokens), cutoff, def (default effort), desc, alias
let modelList = { claude: [{ id: '', label: '', efforts: EFFORTS },
  ...['fable', 'opus', 'sonnet', 'haiku'].map(id => ({ id, label: id[0].toUpperCase() + id.slice(1), alias: true, efforts: EFFORTS }))] };

// Claude Code's /model reads a model catalog compiled into the CLI; the window reads the same catalog there: every model
// with its name, the id to pass, its context, knowledge cutoff and the efforts it takes. Read once per CLI version.
function claudeCatalog(done) {
  let bin = '';
  try {
    const shim = require('child_process').execFileSync(WIN ? 'where' : 'which', ['claude'], { encoding: 'utf8', windowsHide: true }).split(/\r?\n/)[0].trim();
    const dir = path.join(path.dirname(shim), 'node_modules', '@anthropic-ai', 'claude-code', 'bin');
    bin = [path.join(dir, 'claude.exe'), path.join(dir, 'claude'), fs.realpathSync(shim)].find(f => { try { return fs.statSync(f).size > 1e7; } catch { return false; } }) || '';
  } catch {}
  if (!bin) return;
  const st = fs.statSync(bin), cache = path.join(HOME, 'claude-models.json'), key = `2:${st.size}:${st.mtimeMs}`;
  try { const c = JSON.parse(fs.readFileSync(cache, 'utf8')); if (c.key === key) return done(c.models); } catch {}
  const found = new Map(), START = /\{id:"(claude-[a-z0-9-]+)",family:"(\w+)",display_name:"([^"]+)"/g, SPAN = 3000;
  const take = (str, upto) => {
    for (const m of str.matchAll(START)) {
      if (m.index > upto || found.has(m[1])) continue;
      let body = str.slice(m.index, m.index + SPAN);
      const next = body.indexOf('{id:"claude-', 1);
      if (next > 0) body = body.slice(0, next);
      const g = re => (re.exec(body) || [])[1] || '', caps = g(/capabilities:\[([^\]]*)\]/);
      found.set(m[1], { id: g(/first_party:"([^"]+)"/) || m[1], family: m[2], label: m[3], cutoff: g(/knowledge_cutoff:"([^"]*)"/),
        ctx: +g(/context:\{window:([\de.]+)/) || 0, def: g(/default_effort:"(\w+)"/),
        efforts: /"effort"/.test(caps) ? ['low', 'medium', 'high', ...(/"xhigh_effort"/.test(caps) ? ['xhigh'] : []), ...(/"max_effort"/.test(caps) ? ['max'] : [])] : [] });
    }
  };
  let tail = '';
  fs.createReadStream(bin, { encoding: 'latin1', highWaterMark: 1 << 22 })
    .on('data', chunk => { const str = tail + chunk; take(str, str.length - SPAN); tail = str.slice(-SPAN - 200); })
    .on('end', () => {
      take(tail, Infinity);
      const ORDER = ['fable', 'opus', 'sonnet', 'haiku'], ver = x => parseFloat(x.label.split(' ').pop()) || 0;
      const models = [...found.values()].filter(x => ORDER.includes(x.family) && !/^claude-3/.test(x.id))
        .sort((a, b) => ORDER.indexOf(a.family) - ORDER.indexOf(b.family) || ver(b) - ver(a))
        .map(x => ({ id: x.id, label: x.label, efforts: x.efforts, ctx: x.ctx, cutoff: x.cutoff, def: x.def }));
      if (!models.length) return;
      try { fs.writeFileSync(cache, JSON.stringify({ key, models })); } catch {}
      done(models);
    })
    .on('error', () => {});
}

function loadModels() {
  claudeCatalog(list => { modelList.claude = [modelList.claude[0], ...list]; });
  try {  // codex keeps the list its /model shows, with each model's description and what each effort means
    const c = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.codex', 'models_cache.json'), 'utf8'));
    modelList.codex = [{ id: '', label: '', efforts: [] }, ...(c.models || []).filter(m => m.visibility === 'list').map(m => ({
      id: m.slug, label: m.display_name || m.slug, def: m.default_reasoning_level || '', desc: m.description || '', ctx: m.context_window || 0,
      efforts: (m.supported_reasoning_levels || []).map(r => r.effort),
      effortHints: Object.fromEntries((m.supported_reasoning_levels || []).map(r => [r.effort, r.description || ''])) }))];
  } catch { modelList.codex = [{ id: '', label: '', efforts: [] }]; }
  // agy asks its server; once per app start, in the background
  require('child_process').execFile('agy', ['models'], { timeout: 30e3, windowsHide: true }, (e, out) => {
    const list = String(out || '').split('\n').map(l => l.split('\t')).filter(x => x.length === 2 && SAFE.test(x[0].trim()))
      .map(([id, label]) => ({ id: id.trim(), label: label.trim(), efforts: EFFORTS }));
    if (list.length) modelList.agy = list;
  });
}
let onPath;
function available() {
  if (onPath) return onPath;
  onPath = Object.keys(AIS).filter(k => { try { require('child_process').execFileSync(WIN ? 'where' : 'which', [AIS[k].cmd], { stdio: 'ignore', windowsHide: true }); return true; } catch { return false; } });
  return onPath;
}

function chat(req, res) {
  let body = '';
  req.on('data', d => { body += d; if (body.length > 1e6) req.destroy(); });
  req.on('end', () => {
    let q;
    try { q = JSON.parse(body); } catch { res.writeHead(400); return res.end(); }
    const text = String(q.text || '').trim(), cwd = String(q.cwd || ''), ai = AIS[q.ai || 'claude'];
    const L = (pt, en) => q.lang === 'en' ? en : pt;  // the page's language, for what this run says
    let dir = false;
    try { dir = fs.statSync(cwd).isDirectory(); } catch {}
    if (!text || !dir || !ai) { res.writeHead(400); return res.end(L('pedido vazio, pasta que não existe ou IA desconhecida', 'empty request, missing folder or unknown AI')); }
    const ok = v => SAFE.test(v || '') ? v : '';
    // ponytail: claude and codex are .cmd files on Windows, which node only runs through a shell; every arg is fixed or
    // matched SAFE and the prompt goes on stdin, so nothing the user types reaches the shell
    const child = spawn(ai.cmd, ai.args(ok(q.model), ok(q.session), !!q.fork, text, /^[a-z]{2,8}$/.test(q.effort || '') ? q.effort : ''), { cwd, shell: ai.shell, windowsHide: true });
    if (ai.stdin) child.stdin.end(text); else child.stdin.end();
    res.writeHead(200, { 'content-type': 'application/x-ndjson', 'cache-control': 'no-store' });
    let ended = false, exited = false;
    const send = o => { if (o.t === 'end') ended = true; if (!res.writableEnded) res.write(JSON.stringify(o) + '\n'); };
    let buf = '', err = '';
    // subagents the window follows from their own logs; the stream stays open until each one finishes
    const run = { agents: new Set(), kids: new Map(), stops: [], main: '' };
    run.watch = (id, file, fn) => {
      const kid = { last: Date.now() };
      kid.stop = follow(file, d => {
        kid.last = last = Date.now();
        const r = fn(d);
        if (!r) return;
        send({ t: 'agentdone', id, ok: r.ok, s: r.s.replace(/\s+/g, ' ').trim().slice(0, 400) });
        kid.stop(); run.kids.delete(id);
      });
      run.kids.set(id, kid);
    };
    const finish = () => {
      if (res.writableEnded) return;
      run.stops.forEach(f => f());
      for (const k of run.kids.values()) k.stop();
      res.end();
    };
    // ponytail: a subagent silent for 2 minutes counts as stopped (its CLI may have exited under it)
    const reaper = setInterval(() => {
      for (const [id, k] of run.kids) if (Date.now() - k.last > 120e3) { send({ t: 'agentdone', id, ok: false, s: L('sem notícia há 2 min', 'no news for 2 min') }); k.stop(); run.kids.delete(id); }
      if (exited && !run.kids.size) finish();
    }, 2000);
    run.stops.push(() => clearInterval(reaper));
    const line = l => { const d = tryJSON(l); if (d) ai.relay(d, send, run); };
    child.stdout.on('data', d => {
      last = Date.now();
      const lines = (buf + d).split('\n');
      buf = lines.pop();
      lines.forEach(line);
    });
    child.stderr.on('data', d => { err = (err + d).slice(-2000); });
    child.on('error', e => { send({ t: 'end', cost: 0, error: L(`${ai.cmd} não encontrado no PATH: `, `${ai.cmd} not found on PATH: `) + e.message }); finish(); });
    child.on('close', code => {
      if (buf) line(buf);
      if (code && !ended) send({ t: 'end', cost: 0, error: err.trim().split('\n').filter(l => !/^\d{4}-\d\d-\d\dT.*(ERROR|WARN)/.test(l)).pop() || L(`${ai.cmd} saiu com código ${code}`, `${ai.cmd} exited with code ${code}`) });
      else if (!ended) send({ t: 'end', cost: 0, error: '' });
      exited = true;
      if (!run.kids.size) finish();
    });
    // the window closed or the user pressed stop: the run stops too (on Windows the shell's whole tree)
    res.on('close', () => {
      run.stops.forEach(f => f());
      for (const k of run.kids.values()) k.stop();
      if (child.exitCode !== null) return;
      if (WIN) spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { windowsHide: true });
      else child.kill();
    });
  });
}

// Helena's own commands, for the / menu (the CLI runs them: they go as the prompt)
function commands() {
  const dir = path.join(__dirname, '..', 'commands');
  let files = [];
  try { files = fs.readdirSync(dir).filter(f => f.endsWith('.md')); } catch {}
  return files.map(f => ({ name: 'helena:' + f.slice(0, -3), description: field(fs.readFileSync(path.join(dir, f), 'utf8'), 'description').replace(/^"|"$/g, '') }));
}

function serve(port) {
  const page = path.join(__dirname, 'index.html');
  const server = http.createServer((req, res) => {
    const host = req.headers.host || '';
    if (host !== `127.0.0.1:${server.address().port}` && host !== `localhost:${server.address().port}`) { res.writeHead(403); return res.end(); }
    last = Date.now();
    if (req.method === 'POST' && req.url === '/api/chat') {
      if (req.headers['x-helena'] !== TOKEN) { res.writeHead(403); return res.end(); }
      return chat(req, res);
    }
    if (req.method !== 'GET') { res.writeHead(405); return res.end(); }
    if (req.url === '/') {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
      return res.end(fs.readFileSync(page, 'utf8').replace('__TOKEN__', TOKEN));
    }
    if (req.url === '/icon.png') {
      res.writeHead(200, { 'content-type': 'image/png', 'cache-control': 'max-age=86400' });
      return res.end(fs.readFileSync(path.join(__dirname, 'icon.png')));
    }
    if (req.url === '/api/state') {
      let body;
      try { body = JSON.stringify(state()); } catch (e) { res.writeHead(500); return res.end(String(e.message)); }
      res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      return res.end(body);
    }
    res.writeHead(404);
    res.end();
  });
  server.listen(port, '127.0.0.1', () => {
    const url = `http://127.0.0.1:${server.address().port}/`;
    try { fs.mkdirSync(HOME, { recursive: true }); fs.writeFileSync(PORTFILE, String(server.address().port)); } catch {}
    console.log(url);
    open(url);
  });
  setInterval(() => {
    if (Date.now() - last < IDLE) return;
    try { if (fs.readFileSync(PORTFILE, 'utf8') === String(server.address().port)) fs.rmSync(PORTFILE); } catch {}
    process.exit(0);
  }, 10e3).unref();
  server.on('close', () => process.exit(0));
}

if (process.argv.includes('--serve')) {
  loadModels();
  setInterval(loadModels, 10 * 60e3).unref();  // a model the account gains shows up without reopening the window
  serve(+arg('--port', 0));
}
else {
  // one running already: open another window on it instead of starting a second server
  let port = '';
  try { port = fs.readFileSync(PORTFILE, 'utf8').trim(); } catch {}
  const start = () => {
    // detached: on Windows the server then has no console, so every console program it runs needs windowsHide or it
    // pops a visible window (not detached is no way out: libuv kills those children when this launcher exits)
    spawn(process.execPath, [__filename, '--serve', ...process.argv.slice(2)], { detached: true, stdio: 'ignore', windowsHide: true }).unref();
    console.log('Helena app opening in its own window. It closes by itself a minute after the window does.');
  };
  if (!port) start();
  else http.get({ host: '127.0.0.1', port, path: '/api/state', timeout: 1500 }, res => {
    res.resume();
    if (res.statusCode !== 200) return start();
    open(`http://127.0.0.1:${port}/`);
    console.log(`Helena app already running: http://127.0.0.1:${port}/`);
  }).on('error', start).on('timeout', function () { this.destroy(); });
}
