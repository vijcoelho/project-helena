// UserPromptSubmit: runs on every request, no LLM, a few milliseconds. It:
//  - loads only the kits the request needs (the rest of the library stays out of context)
//  - hands over the 2 memory notes that match the request, so Claude does not spend a round trip reading them
//  - turns a plugin back on when the request needs one Helena turned off in this project
//  - warns by real context size: every message re-reads the whole context, the biggest cost there is
//  - warns near the plan's usage limit and names another installed AI with room (limits.js)
//  - hints a cheaper model for routine requests and a Haiku subagent for broad searches
//  - every 6 prompts, distills the new turns in the background, so ideas reach Obsidian mid-session
// ponytail: word overlap for notes and kits; swap for embeddings if it starts missing obvious matches.
const fs = require('fs'), path = require('path');
const { bg, HOME, LIBRARY, KITS, MEMORY } = require('./paths');
if (process.env.HELENA_DISTILLING) process.exit(0);
const CHECKPOINT = 6; // prompts between mid-session distills
const LONG = [120e3, 250e3, 500e3]; // context tokens at which the session-length warning fires (once each)
const STOP = new Set(('que para com uma por mais isso esse essa este esta aqui como quando onde tudo todo toda voce pode faz ' +
  'fazer tem ter vai vamos agora ainda depois the and for with this that from your you can make just then into have has are ' +
  'was will what when where which there also all any not but our out use get').split(' '));
const words = t => new Set((t.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').match(/[a-z][a-z0-9-]{2,}/g) || [])
  .filter(w => !STOP.has(w)));
const load = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
const once = (session, key) => {  // true the first time this session asks for `key`
  const flag = path.join(HOME, 'warnings', `${session}-${key}`);
  if (fs.existsSync(flag)) return false;
  fs.mkdirSync(path.dirname(flag), { recursive: true });
  fs.writeFileSync(flag, '');
  return true;
};

let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let ev = {};
  try { ev = JSON.parse(input); } catch {}
  const prompt = ev.prompt || '', asked = words(prompt), session = ev.session_id || 'x', cwd = ev.cwd || process.cwd();
  const out = [], stats = load(path.join(HOME, 'stats.json'), { notes: {}, skills: {} });
  const today = new Date().toISOString().slice(0, 10);

  // ---- kits: a regex `trigger`, or `keywords` with a minimum number of them in the request (Helena's own skills)
  const where = {};
  try {
    const catalog = fs.readFileSync(path.join(LIBRARY, 'CATALOG.md'), 'utf8');
    for (const m of catalog.matchAll(/^- \*\*(.+?)\*\*:[\s\S]*?`([^`]+SKILL\.md)`/gm)) where[m[1]] ??= m[2];
  } catch {}
  for (const [name, k] of Object.entries(load(KITS, {}))) {
    const hit = k.trigger ? new RegExp(k.trigger, 'i').test(prompt)
      : (k.keywords || []).filter(w => asked.has(w)).length >= (k.min || 1);
    if (!hit) continue;
    const always = (k.always || []).filter(s => where[s]);
    const extra = (k.on_demand || []).filter(s => where[s]);
    if (name.startsWith('auto:')) for (const s of always) stats.skills[s] = { last: today, uses: ((stats.skills[s] || {}).uses || 0) + 1 };
    out.push(`Helena: kit "${name}".` +
      (always.length ? ' Read before coding: ' + always.map(s => where[s]).join(' , ') + '.' : '') +
      ((k.skills || []).length ? ' Use: ' + k.skills.join(', ') + '.' : '') +
      (extra.length ? ' If needed (paths in ~/.helena/library/CATALOG.md): ' + extra.join(', ') + '.' : '') +
      (k.note ? ' ' + k.note : ''));
  }

  // ---- memory: the notes sharing the most words with the request, delivered whole (each only once per session)
  try {
    const scored = fs.readdirSync(MEMORY).filter(f => f.endsWith('.md')).map(f => {
      const text = fs.readFileSync(path.join(MEMORY, f), 'utf8');
      const head = words(f.slice(0, -3).replace(/-/g, ' ') + ' ' + ((text.match(/^description:\s*(.+)$/m) || [])[1] || ''));
      const body = words(text.slice(0, 1500));
      let score = 0;
      for (const w of asked) score += head.has(w) ? 2 : body.has(w) ? 1 : 0;
      return { f, text, score };
    }).filter(n => n.score >= 3).sort((a, b) => b.score - a.score).slice(0, 2);
    for (const n of scored) {
      if (!once(session, 'note-' + n.f)) continue;
      out.push(`Helena memory (${n.f}), relevant to this request:\n` + n.text.replace(/^---[\s\S]*?---\n/, '').trim().slice(0, 900));
      const slug = n.f.slice(0, -3);
      stats.notes[slug] = { last: today, hits: ((stats.notes[slug] || {}).hits || 0) + 1 };
    }
  } catch {}

  // ---- plugins Helena turned off here come back when the request needs them (they load on the next session start)
  const profiles = load(path.join(HOME, 'profiles.json'), {}), plugins = load(path.join(HOME, 'plugins.json'), {});
  const key = Object.keys(profiles).find(k => path.resolve(k).toLowerCase() === path.resolve(cwd).toLowerCase());
  if (key) {
    const local = path.join(profiles[key].cwd, '.claude', 'settings.local.json');
    const back = profiles[key].off.filter(p => (plugins[p] ? plugins[p].keywords : [p.split('@')[0]]).some(w => asked.has(w)));
    if (back.length) {
      const s = load(local, {});
      for (const p of back) delete (s.enabledPlugins || {})[p];
      fs.writeFileSync(local, JSON.stringify(s, null, 1));
      profiles[key].off = profiles[key].off.filter(p => !back.includes(p));
      profiles[key].restored = [...new Set([...(profiles[key].restored || []), ...back])];
      fs.writeFileSync(path.join(HOME, 'profiles.json'), JSON.stringify(profiles, null, 1));
      out.push(`Helena: this request needs ${back.map(p => p.split('@')[0]).join(', ')}, which was off in this project. ` +
        'It is back on, and plugins load when a session starts. Tell the user in one line: save HANDOFF.md if needed, ' +
        'restart Claude Code in this folder, and the plugin will be there.');
    }
  }

  // ---- real context size, from the last assistant message's usage (read from the end of the transcript only)
  let ctx = 0, model = '';
  try {
    const fd = fs.openSync(ev.transcript_path, 'r'), size = fs.fstatSync(fd).size, n = Math.min(size, 256 * 1024);
    const buf = Buffer.alloc(n);
    fs.readSync(fd, buf, 0, n, size - n);
    fs.closeSync(fd);
    for (const line of buf.toString('utf8').split('\n').reverse()) {
      const u = line.includes('"usage"') && line.includes('"assistant"') && (() => { try { return JSON.parse(line).message; } catch {} })();
      if (u && u.usage) { ctx = u.usage.input_tokens + u.usage.cache_creation_input_tokens + u.usage.cache_read_input_tokens; model = u.model || ''; break; }
    }
  } catch {}
  const mark = LONG.filter(x => ctx >= x).pop();
  // with the mod loaded, the interface shows the 120k warning for free; 250k+ still asks Claude for HANDOFF.md
  const modOn = fs.existsSync(path.join(HOME, 'warnings', `${session}-mod`));
  if (mark && !(modOn && mark < 250e3) && once(session, 'ctx-' + mark))
    out.push(`Helena: this session's context is ${Math.round(ctx / 1000)}k tokens and every message re-reads all of it. ` +
      (mark >= 250e3 ? 'Before answering anything else, write HANDOFF.md (Done / Next / How to run / Decisions) and ' : 'When this request is done, ') +
      'tell the user in one line to start fresh with /clear: HANDOFF.md and memory carry over, the cost resets.');

  // ---- plan limit: save the work and point at an AI with room before this one runs out (once per level per session)
  try {
    const me = !ev.transcript_path ? '' : /[\\/]\.codex[\\/]/.test(ev.transcript_path) ? 'codex' : 'claude';
    const w = me && require('./limits').warn(me);
    if (w && once(session, 'limit-' + w.level)) out.push(w.text);
  } catch {}

  // ---- cheaper paths for cheap work
  if (/opus/i.test(model) && prompt.length < 120 &&
      /^\s*(commit|comita|commita|push|faz (o )?(commit|push)|roda|rodar|run|start|para|stop|renomeia|rename|instala|install)\b/i.test(prompt) &&
      once(session, 'model-hint'))
    out.push('Helena: routine request on Opus. After it, mention in one line that `/model sonnet` does this kind of task for a fraction of the limit.');
  if (/(onde (fica|est[aá]|tem)|where (is|are)|find (all|every)|acha (todos|todas|onde)|mapeia|map (the|out)|lista todos|list all)/i.test(prompt))
    out.push('Helena: broad search. Delegate it to the Explore subagent with model "haiku" and keep only its conclusion here.');

  // ---- a git rule said in chat is gone next session; in .helena/git the guard hook enforces it every time
  if (/(n[aã]o|nunca|never|don'?t|do not|stop)\b[^.\n]{0,40}\b(commit|comit|main|push)|\b(commit|comit)\w*\b[^.\n]{0,40}\b(n[aã]o|nunca|s[oó]|never|only)\b/i.test(prompt))
    out.push('Helena: if this is a git rule that holds for this project (e.g. "never commit to main", "don\'t commit videos"), ' +
      'save it in .helena/git at the repo root, one rule per line: `main: no` and/or `never: <globs like in .gitignore>`. ' +
      'From then on the guard hook blocks any commit that breaks it.');

  // ---- checkpoint: distill.py keeps its own offset, so it only reads the turns since the last run
  if (!process.env.HELENA_EVAL && ev.transcript_path) try {
    const f = path.join(HOME, 'warnings', `${session}-prompts`), n = (+load(f, 0) || 0) + 1;
    fs.mkdirSync(path.dirname(f), { recursive: true });
    fs.writeFileSync(f, String(n));
    if (n % CHECKPOINT === 0) bg('distill.py', [ev.transcript_path], 'distill.log');
  } catch {}

  try { fs.writeFileSync(path.join(HOME, 'stats.json'), JSON.stringify(stats)); } catch {}
  if (out.length) console.log(out.join('\n'));
});
