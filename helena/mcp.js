// helena-mcp: Helena for any AI that speaks MCP (Gemini CLI, Qwen Code, Kimi, opencode, Antigravity, Cursor...).
// Same brain as the Claude Code hooks: it runs start.js and router.js and writes notes through distill.py,
// so memory, kits and the library stay one thing, in one Obsidian vault, whatever model is talking.
// Stdio JSON-RPC, one message per line, no dependencies. Register it with: python helena/connect.py
const fs = require('fs'), path = require('path'), { spawnSync } = require('child_process');
const { LIBRARY } = require('./hooks/paths');
const SESSION = 'mcp-' + process.pid;  // router.js hands each memory note once per session; one server = one session
const VERSION = require('./.claude-plugin/plugin.json').version;

const INSTRUCTIONS = `Helena is the user's memory and skill library, shared by every AI they use.
Helena comes first: use her before any other memory tool (Sinapse, a memory MCP, a graph), and when one of those
fails or finds nothing, still ask Helena before answering that you do not know.
- At the start of a conversation, call helena_start with the folder you are working in.
- Before each new request, call helena_context with the request: it returns the notes and skills that match.
- When it names a skill, read it with helena_skill and follow it.
- When the user corrects you or states something that holds from now on, call helena_remember (one fact per note).`;
if (process.argv[2] === '--instructions') { console.log(INSTRUCTIONS); process.exit(0); }  // connect.py copies it

const node = (script, cwd, input) => spawnSync('node', [path.join(__dirname, 'hooks', script)], {
  cwd: cwd && fs.existsSync(cwd) ? cwd : process.cwd(), input, encoding: 'utf8', timeout: 15000, windowsHide: true,
}).stdout || '';

const TOOLS = {
  helena_start: {
    description: 'Session brief: HANDOFF.md, project brief from git, the memory index for this project. Call once at the start.',
    props: { cwd: 'Absolute path of the folder you are working in' }, required: ['cwd'],
    run: a => node('start.js', a.cwd),
  },
  helena_context: {
    description: 'The memory notes and skill kits that match a request. Call before working on each new request.',
    props: { request: "The user's request, verbatim", cwd: 'Absolute path of the folder you are working in' }, required: ['request'],
    run: a => node('router.js', a.cwd, JSON.stringify({ prompt: a.request, cwd: a.cwd, session_id: SESSION })),
  },
  helena_skill: {
    description: "Full text of a skill from Helena's library (the names helena_context returns). Relative paths inside it start from its folder.",
    props: { name: 'Skill name, e.g. design-taste-frontend' }, required: ['name'],
    run: a => {
      const f = path.join(LIBRARY, path.basename(a.name), 'SKILL.md');
      return fs.existsSync(f) ? `Folder: ${path.dirname(f)}\n\n` + fs.readFileSync(f, 'utf8') : `No skill "${a.name}". See ${path.join(LIBRARY, 'CATALOG.md')}`;
    },
  },
  helena_remember: {
    description: 'Save one durable fact: a correction, a preference, a rule, a project decision. Same slug adds to an existing note.',
    props: {
      slug: 'kebab-case name', type: 'rule | preference | fact | user', description: 'One line',
      body: 'Short markdown, with the why', project: 'Folder name if it only applies to that project, else empty',
      checks: 'Files the fact depends on, relative to the project ("src/db.js, src/db.js#connectPostgres"); flagged when they go',
      supersedes: 'Slug of the note this fact replaces (it gets archived), else empty',
    },
    required: ['slug', 'description', 'body'],
    run: a => {
      const r = spawnSync('python', [path.join(__dirname, 'distill.py'), '--remember', 'mcp'], {
        input: JSON.stringify({ memories: [a] }), encoding: 'utf8', timeout: 15000, windowsHide: true,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
      });
      return r.status === 0 ? 'Saved: ' + r.stdout.trim() : 'Not saved: ' + (r.stderr || r.error || '').toString().trim().slice(-300);
    },
  },
  helena_limits: {
    description: "How much of each AI plan's usage limit is gone (5 hours and week), and whether the week lasts at this pace.",
    props: {}, required: [],
    run: () => spawnSync('node', [path.join(__dirname, 'hooks', 'limits.js')], { encoding: 'utf8', timeout: 15000, windowsHide: true }).stdout || '',
  },
  helena_rewind: {
    description: 'Undo: list the snapshots Helena took before each request, or put the folder back n requests (git repos).',
    props: { cwd: 'Absolute path of the folder', n: 'How many requests back; empty lists the snapshots' }, required: ['cwd'],
    run: a => spawnSync('node', [path.join(__dirname, 'hooks', 'rewind.js'), String(a.n || '')], {
      cwd: a.cwd && fs.existsSync(a.cwd) ? a.cwd : process.cwd(), encoding: 'utf8', timeout: 30000, windowsHide: true }).stdout || '',
  },
  helena_recall: {
    description: 'Search past Claude Code sessions for what was asked or decided about something. All words must match.',
    props: { words: 'Words to find, space separated', days: 'How many days back (default 30)' }, required: ['words'],
    run: a => spawnSync('python', [path.join(__dirname, 'history.py'), 'recall', ...String(a.words).split(/\s+/).filter(Boolean), '--days', String(a.days || 30)], {
      encoding: 'utf8', timeout: 30000, windowsHide: true, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } }).stdout || '',
  },
};

const send = m => process.stdout.write(JSON.stringify({ jsonrpc: '2.0', ...m }) + '\n');
const handle = msg => {
  const { id, method, params = {} } = msg;
  if (method === 'initialize') return send({ id, result: {
    protocolVersion: params.protocolVersion || '2025-06-18', capabilities: { tools: {} },
    serverInfo: { name: 'helena', version: VERSION }, instructions: INSTRUCTIONS,
  } });
  if (method === 'tools/list') return send({ id, result: { tools: Object.entries(TOOLS).map(([name, t]) => ({
    name, description: t.description, inputSchema: { type: 'object', required: t.required,
      properties: Object.fromEntries(Object.entries(t.props).map(([k, d]) => [k, { type: 'string', description: d }])) },
  })) } });
  if (method === 'tools/call') {
    const t = TOOLS[params.name];
    if (!t) return send({ id, error: { code: -32602, message: `Unknown tool ${params.name}` } });
    let text;
    try { text = t.run(params.arguments || {}).trim() || '(nothing for this one)'; } catch (e) { text = 'Error: ' + e.message; }
    return send({ id, result: { content: [{ type: 'text', text }] } });
  }
  if (method === 'ping') return send({ id, result: {} });
  if (id !== undefined) send({ id, error: { code: -32601, message: `Method not found: ${method}` } });
};

let buf = '';
process.stdin.on('data', d => {
  buf += d;
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i).trim();
    buf = buf.slice(i + 1);
    if (line) try { handle(JSON.parse(line)); } catch { send({ id: null, error: { code: -32700, message: 'Parse error' } }); }
  }
});
