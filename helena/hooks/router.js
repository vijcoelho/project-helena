// UserPromptSubmit: runs on every request, no LLM, a few milliseconds. It:
//  - loads only the kits the request needs, once per session (the rest of the library stays out of context)
//  - hands over the 2 memory notes that match the request, so Claude does not spend a round trip reading them
//  - turns a plugin back on when the request needs one Helena turned off in this project
//  - warns by real context size: every message re-reads the whole context, the biggest cost there is
//  - warns near the plan's usage limit and names another installed AI with room, and when the week runs out before it resets (limits.js)
//  - snapshots the working tree before the AI works, so /helena:rewind undoes a turn in any CLI (rewind.js)
//  - messages that are not the user's (a subagent's report, a task notification) get none of the request-matching parts
//  - hints a cheaper model for routine requests and a Haiku subagent for broad searches
//  - on a redo ("try again", "that's not it"), has the AI say what went wrong before it spends another attempt
//  - every 6 prompts, distills the new turns in the background, so ideas reach Obsidian mid-session
// ponytail: word overlap for notes and kits; swap for embeddings if it starts missing obvious matches.
const fs = require('fs'), path = require('path');
const { bg, HOME, LIBRARY, KITS } = require('./paths');
const { field, notes, mark: stale } = require('./memory');
if (process.env.HELENA_DISTILLING) process.exit(0);
const CHECKPOINT = 6; // prompts between mid-session distills
const LONG = [120e3, 250e3, 500e3]; // context tokens at which the session-length warning fires (once each)
const STOP = new Set(('que para com uma por mais isso esse essa este esta aqui como quando onde tudo todo toda voce pode faz ' +
  'fazer tem ter vai vamos agora ainda depois the and for with this that from your you can make just then into have has are ' +
  'was will what when where which there also all any not but our out use get').split(' '));
// "try again", "undo that and redo it", "that's not what I asked", in Portuguese and English
const REDO = new RegExp('\\b(tenta|tente|faz|fa[cç]a|try|do (it|that|this))\\s+(de novo|novamente|outra vez|again)\\b|' +
  '\\b(desfaz|desfa[cç]a|reverte|undo|revert)\\b[^.\\n]{0,40}\\b(refaz|refa[cç]a|redo|de novo|again)\\b|' +
  '\\bn[aã]o (era|foi) isso\\b|\\bnot what i (asked|wanted|meant)\\b', 'i');
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
  // a subagent's report or a task notification arrives as a prompt too: its words are not a request for a kit or a plugin
  const human = !/^\s*(Another Claude session sent a message|<(task-notification|agent-message|system-reminder|local-command-\w+|command-\w+)\b)/.test(ev.prompt || '');
  const prompt = human ? ev.prompt || '' : '', asked = words(prompt), session = ev.session_id || 'x', cwd = ev.cwd || process.cwd();
  const out = [], stats = load(path.join(HOME, 'stats.json'), { notes: {}, skills: {} });
  const today = new Date().toISOString().slice(0, 10);
  // a new request of the user's: delegate.js counts workers per request (the file only exists once that hook is in use)
  const workers = path.join(HOME, 'warnings', `${session}-workers`);
  if (human && fs.existsSync(workers)) try { fs.appendFileSync(workers, '{"t":"turn"}\n'); } catch {}

  // ---- kits: a regex `trigger`, or `keywords` with a minimum number of them in the request (Helena's own skills)
  const where = {};
  try {
    const catalog = fs.readFileSync(path.join(LIBRARY, 'CATALOG.md'), 'utf8');
    for (const m of catalog.matchAll(/^- \*\*(.+?)\*\*:[\s\S]*?`([^`]+SKILL\.md)`/gm)) where[m[1]] ??= m[2];
  } catch {}
  for (const [name, k] of Object.entries(load(KITS, {}))) {
    const hit = k.trigger ? new RegExp(k.trigger, 'i').test(prompt)
      : (k.keywords || []).filter(w => asked.has(w)).length >= (k.min || 1);
    if (!hit || !once(session, 'kit-' + name)) continue;  // already in context this session: repeating it only costs tokens
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
    const scored = notes(cwd).map(n => {
      const head = words(n.slug.replace(/-/g, ' ') + ' ' + field(n.text, 'description'));
      const body = words(n.text.slice(0, 1500));
      let score = 0;
      for (const w of asked) score += head.has(w) ? 2 : body.has(w) ? 1 : 0;
      return { ...n, score };
    }).filter(n => n.score >= 3).sort((a, b) => b.score - a.score).slice(0, 2);
    for (const n of scored) {
      if (!once(session, 'note-' + n.file)) continue;
      out.push(`Helena memory (${n.file})${stale(n)}, relevant to this request:\n` + n.text.replace(/^---[\s\S]*?---\n/, '').trim().slice(0, 900));
      stats.notes[n.slug] = { last: today, hits: ((stats.notes[n.slug] || {}).hits || 0) + 1 };
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
    const limits = me && require('./limits'), w = me && limits.warn(me);
    if (w && once(session, 'limit-' + w.level)) out.push(w.text);
    else if (me && once('day', `pace-${me}-${today}`)) {  // the weekly pace, at most once a day
      const p = limits.paceWarn(me);
      if (p) out.push(p);
      else fs.rmSync(path.join(HOME, 'warnings', `day-pace-${me}-${today}`), { force: true });  // nothing to say yet: ask again later
    }
  } catch {}

  // ---- undo for any CLI: the folder as it was before this request (git repos only; nothing is staged or committed)
  if (!process.env.HELENA_EVAL) try { require('./rewind').snapshot(cwd, prompt.replace(/\s+/g, ' ').slice(0, 60) || 'agent message'); } catch {}

  // ---- cheaper paths for cheap work. Never `/model` mid-session: the switch re-reads the whole history uncached and
  //      `/model <name>` becomes the default for new sessions (code.claude.com/docs/en/prompt-caching#switching-models)
  // ponytail: 50k floor because a fresh subagent starts at ~44k tokens; below it, inline is cheaper. Tune with the 1.3.0 meter
  if (/opus/i.test(model) && ctx >= 50e3 && prompt.length < 120 &&
      /^\s*(roda|rodar|run|instala|install)\b/i.test(prompt) && once(session, 'model-hint'))
    out.push(`Helena: routine command on Opus with ${Math.round(ctx / 1000)}k of context. If its output will be long (tests, install, build), ` +
      'run it in a subagent with model "haiku" and keep only the result here.');
  if (/(onde (fica|est[aá]|tem)|where (is|are)|find (all|every)|acha (todos|todas|onde)|mapeia|map (the|out)|lista todos|list all)/i.test(prompt))
    out.push('Helena: broad search. Delegate it to the Explore subagent with model "haiku" and keep only its conclusion here.');

  // ---- a redo is the most expensive turn: the failed attempt stays in context and is paid again on every message
  if (REDO.test(prompt))
    out.push('Helena: this is a redo. Before changing anything, say in one line what the last attempt got wrong and what ' +
      'you will do differently; if the request can still be read two ways, ask one question first instead of guessing ' +
      'again. `/helena:rewind` puts the folder back as it was before the last request.');

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
