// Where Helena keeps the user's data. Everything learned lives here, outside the plugin, so updates never wipe it.
//   ~/.helena/vault        one line: path of the Obsidian vault (default ~/Helena)
//   ~/.helena/kits.json    the user's kits (see helena/kits.example.json)
//   ~/.helena/library/     skills that only load when a kit asks for them
//   ~/.helena/audit.jsonl  every time a hook blocked or asked about something (/helena:audit, exportable for a team)
//   ~/.helena/egress.jsonl every host, search and MCP server the AI reached (/helena:audit lists them)
const fs = require('fs'), path = require('path'), os = require('os'), { spawn } = require('child_process');
const HOME = path.join(os.homedir(), '.helena');
const readVault = () => { try { return fs.readFileSync(path.join(HOME, 'vault'), 'utf8').trim(); } catch {} };
const VAULT = process.env.HELENA_VAULT || readVault() || path.join(os.homedir(), 'Helena');
// runs a helena/*.py script detached, output appended to ~/.helena/<log>; the hook exits right away
const bg = (script, args, log) => {
  fs.mkdirSync(HOME, { recursive: true });
  const fd = fs.openSync(path.join(HOME, log), 'a');
  spawn('python', [path.join(__dirname, '..', script), ...args], {
    detached: true, windowsHide: true, stdio: ['ignore', fd, fd],
    env: { ...process.env, HELENA_DISTILLING: '1', PYTHONIOENCODING: 'utf-8' },
  }).unref();
};
// same pattern as guard.js and distill.py (SECRET)
const SECRET = /\b(sk[_-][A-Za-z0-9_-]{16,}|[a-f0-9]{40,}|(pk|rk)_(live|test)_[A-Za-z0-9]{10,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|\d{8,}:[A-Za-z0-9_-]{30,})/g;
// one line per hook decision; what was attempted is cut short and keys are masked
const audit = (ev, hook, decision, why) => {
  try {
    const t = ev.tool_input || {};
    fs.mkdirSync(HOME, { recursive: true });
    fs.appendFileSync(path.join(HOME, 'audit.jsonl'), JSON.stringify({
      ts: new Date().toISOString().slice(0, 19), project: path.basename(ev.cwd || process.cwd()), session: ev.session_id || '',
      hook, tool: ev.tool_name || '', decision,
      what: String(t.command || t.file_path || t.pattern || '').slice(0, 160).replace(SECRET, '***'),
      why: String(why).split('\n')[0].slice(0, 200),
    }) + '\n');
  } catch {}
};
// where the AI reached outside this machine: a fetched host, a web search, an MCP server, a URL in a command
const egress = (ev, to) => {
  try {
    fs.mkdirSync(HOME, { recursive: true });
    fs.appendFileSync(path.join(HOME, 'egress.jsonl'), JSON.stringify({
      ts: new Date().toISOString().slice(0, 19), project: path.basename(ev.cwd || process.cwd()), session: ev.session_id || '',
      tool: ev.tool_name || '', to: String(to).split('@').pop().slice(0, 80),  // user:password@host keeps the host only
    }) + '\n');
  } catch {}
};
// tool calls the AI made since the user's last message. Reads the transcript from the end: it reaches megabytes and the
// Stop hooks run on every turn, so parsing all of it each time was the slowest thing Helena did.
const turnTools = transcript => {
  const fd = fs.openSync(transcript, 'r'), size = fs.fstatSync(fd).size;
  try {
    for (let n = 1 << 20; ; n *= 4) {
      const len = Math.min(n, size), buf = Buffer.alloc(len), tools = [];
      fs.readSync(fd, buf, 0, len, size - len);
      const lines = buf.toString('utf8').split('\n');
      if (len < size) lines.shift();  // cut in half
      for (const line of lines.reverse()) {
        let d;
        try { d = JSON.parse(line); } catch { continue; }
        const c = d.message && d.message.content;
        if (d.type === 'user' && (typeof c === 'string' || (Array.isArray(c) && c.some(b => b.type === 'text')))) return tools;
        if (d.type === 'assistant' && Array.isArray(c)) tools.push(...c.filter(b => b.type === 'tool_use'));
      }
      if (len === size) return tools;
    }
  } finally { fs.closeSync(fd); }
};
module.exports = { audit, bg, egress, turnTools, HOME, VAULT, MEMORY: path.join(VAULT, 'Memory'), LIBRARY: path.join(HOME, 'library'), KITS: path.join(HOME, 'kits.json') };
