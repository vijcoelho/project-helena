"""Helena's background worker. Runs at most once every 20 hours, started by the session hooks; never blocks you.

    python helena/worker.py          # respects the 20h throttle
    python helena/worker.py --now    # run right away

1. Plugin profiles: in a project with 3+ sessions, plugins it never used are turned off there (project
   .claude/settings.local.json). Plugins with hooks are never touched. The router turns one back on when a request needs it.
2. Repeated requests: your prompts are grouped by similarity. A group used 20+ times, or 5+ times across 2+ sessions,
   is offered to Haiku, which writes a skill only if there is a reusable procedure Claude would not do well by default.
3. Inbox candidates from distillation that showed up in 2+ sessions become skills directly (no LLM call).
4. Skills Helena created and nobody used for 30 days are removed.
New skills go to ~/.helena/library (zero context until a kit loads them) and you are told at the next session start,
with the command to delete it.
"""
import datetime, json, os, pathlib, re, shutil, subprocess, sys, time, unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from history import HOME, ledger, plugin_of, sessions  # noqa: E402
from distill import SECRET, VAULT, slug  # noqa: E402

LIB = HOME / 'library'
STATE = HOME / 'patterns.json'
MAX_NEW_SKILLS = 3          # Haiku calls per run for skill writing
STOP = set('''que para com uma por mais isso esse essa este esta aqui ali como quando onde tudo todo toda voce você
pode faz fazer tem ter vai vamos agora ainda depois antes sobre muito pra pro the and for with this that from your you
can could would should please make just then into have has are was were will what when where which there their them
also all any not but our out use using get put let its it's sim nao não the'''.split())
KNOWN = {  # words that mean "I need this plugin"; besides these, only the plugin's name and its hyphenated skill names count
    'stripe': 'stripe pagamento pagamentos payment payments checkout gateway assinatura subscription billing cobranca',
    'vercel': 'vercel nextjs',
    'figma': 'figma',
    'nano-banana': 'nano-banana banana imagem imagens image images ilustracao illustration',
    'promo-video': 'promocional remotion',
    'frontend-design': 'landing frontend',
    'mattpocock-skills': 'tdd mattpocock',
    'rust-analyzer-lsp': 'rust cargo',
}
TEMP = os.path.normcase(os.path.realpath(__import__('tempfile').gettempdir()))


def real_project(cwd):
    """Benchmark and scratch sessions run in temp folders; they are not your projects or your habits."""
    return bool(cwd) and not os.path.normcase(os.path.realpath(cwd)).startswith(TEMP)


def words(text):
    text = unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode()
    return {w for w in re.findall(r'[a-z][a-z0-9-]{2,}', text) if w not in STOP}


def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')


def news(text):
    items = load(HOME / 'news.json', [])
    save(HOME / 'news.json', items + [text])


# ---------- 1. plugin profiles

def plugin_catalog():
    """Every user-enabled plugin: does it have hooks (never turned off) and which words mean you need it."""
    settings = load(pathlib.Path.home() / '.claude' / 'settings.json', {})
    installed = load(pathlib.Path.home() / '.claude' / 'plugins' / 'installed_plugins.json', {}).get('plugins', {})
    out = {}
    for key, on in settings.get('enabledPlugins', {}).items():
        if not on:
            continue
        name = key.split('@')[0]
        root = pathlib.Path((installed.get(key) or [{}])[0].get('installPath', ''))
        manifest = load(root / '.claude-plugin' / 'plugin.json', {})
        hooks = (root / 'hooks' / 'hooks.json').exists() or 'hooks' in manifest
        parts = [re.sub(r'\.md$', '', p.name) for d in ('skills', 'commands') if (root / d).is_dir() for p in (root / d).iterdir()]
        kw = set(KNOWN.get(name, '').split()) | {name} | {p for p in parts if re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)+', p)}
        out[key] = {'name': name, 'hooks': hooks, 'keywords': sorted(kw)}
    save(HOME / 'plugins.json', out)
    return out


def profiles(catalog, all_sessions):
    by_project = {}
    for s in all_sessions:
        if not real_project(s['cwd']):
            continue
        p = by_project.setdefault(os.path.normcase(s['cwd']), {'cwd': s['cwd'], 'sessions': 0, 'used': set()})
        p['sessions'] += 1
        p['used'] |= {plugin_of(name) for _, name, _ in s['tools']} - {None}
    done = load(HOME / 'profiles.json', {})
    home = os.path.normcase(str(pathlib.Path.home()))
    for key, p in by_project.items():
        folder = pathlib.Path(p['cwd'])
        if p['sessions'] < 3 or key == home or len(folder.parts) < 3 or not folder.is_dir():
            continue  # too little history, or the home folder / a drive root (their settings are not per project)
        local = folder / '.claude' / 'settings.local.json'
        settings = load(local, {})
        enabled = settings.setdefault('enabledPlugins', {})
        off = [k for k, c in catalog.items()
               if not c['hooks'] and c['name'] not in p['used'] and c['name'] != 'helena' and k not in enabled
               and k not in done.get(key, {}).get('restored', [])
               and not (c['name'] == 'rust-analyzer-lsp' and (folder / 'Cargo.toml').exists())]
        if not off:
            continue
        for k in off:
            enabled[k] = False
        save(local, settings)
        entry = done.setdefault(key, {'cwd': p['cwd'], 'off': [], 'restored': []})
        entry['off'] = sorted(set(entry['off']) | set(off))
        news(f'Helena turned off {len(off)} unused plugin(s) in {folder.name} '
             f'({", ".join(catalog[k]["name"] for k in off)}). Each comes back on its own when a request needs it.')
    save(HOME / 'profiles.json', done)


# ---------- 2. repeated requests -> skills

NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)  # see distill.py: no visible window for claude.exe


def ask_haiku(prompt):
    claude = shutil.which('claude') or 'claude'
    r = subprocess.run([claude, '-p', '--model', 'haiku', '--output-format', 'json', '--tools', '', '--no-session-persistence'],
                       input=prompt, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300,
                       env=dict(os.environ, HELENA_DISTILLING='1'), cwd=pathlib.Path.home(), creationflags=NO_WINDOW)
    out = json.loads(r.stdout or '{}')
    u = out.get('usage') or {}
    ledger({'what': 'worker-skill', 'cost': out.get('total_cost_usd', 0),
            'tokens': sum(u.get(x, 0) for x in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'))})
    m = re.search(r'\{.*\}', out.get('result', ''), re.S)
    return json.loads(m.group(0)) if m else None


SKILL_PROMPT = """A user keeps asking an AI coding assistant for the same kind of thing. Below are their requests and what
the assistant did each time. Decide whether a SKILL (a short recipe the assistant reads before acting) would make this
faster or more correct next time.

Answer worth=false when the assistant already does it well with no recipe (commit, push, run the project, fix a typo,
generic questions), when the requests do not share a real procedure, or when it is about one specific bug.
Answer worth=true only for a repeatable multi-step procedure with specifics worth remembering (exact commands, paths,
tools, order of steps, gotchas the assistant hit before).

Never put secrets, keys or passwords in the skill. Write in the language of the requests.

Answer ONLY with JSON:
{{"worth": true|false, "name": "kebab-case", "description": "when to use it, one sentence",
  "keywords": ["4-8 words the user types when they need this"], "steps": "markdown recipe, under 40 lines"}}

REQUESTS AND ACTIONS ({uses} times in {n_sessions} sessions):
{examples}"""


def install_skill(name, description, steps, keywords, source):
    name = slug(name)
    folder = LIB / name
    if folder.exists():
        return None
    folder.mkdir(parents=True)
    today = datetime.date.today().isoformat()
    (folder / 'SKILL.md').write_text(SECRET.sub('***', f'---\nname: {name}\ndescription: {description}\ncreated-by: helena\n'
                                     f'created: {today}\nsource: {source}\n---\n\n{steps.strip()}\n'), encoding='utf-8')
    with open(LIB / 'CATALOG.md', 'a', encoding='utf-8') as f:
        f.write(f"- **{name}**: {description[:120]}  \n  `{(folder / 'SKILL.md').as_posix()}`\n")
    kits = load(HOME / 'kits.json', {})
    kits[f'auto:{name}'] = {'keywords': sorted(keywords)[:8], 'min': 2 if len(keywords) > 2 else 1, 'always': [name]}
    save(HOME / 'kits.json', kits)
    news(f'Helena created the skill "{name}" ({description}) because {source}. It only loads when a request needs it. '
         f'Don\'t want it? /helena:undo {name}')
    return name


def patterns(all_sessions, state):
    clusters = state.setdefault('clusters', [])
    seen = set(state.setdefault('seen_prompts', []))
    for s in all_sessions:
        if not real_project(s['cwd']):
            continue
        for p in s['prompts']:
            key = f"{s['id']}:{p['ts']}"
            if key in seen or len(p['text']) > 600:
                continue  # already counted, or a pasted spec rather than a request
            seen.add(key)
            w = words(p['text'])
            if len(w) < 3:
                continue  # "commit and push" does not need a skill
            best = max(clusters, key=lambda c: len(w & set(c['top'])) / len(w | set(c['top'])), default=None)
            if best and len(w & set(best['top'])) / len(w | set(best['top'])) >= .45:
                c = best
            else:
                c = {'top': sorted(w), 'counts': {}, 'uses': 0, 'sessions': [], 'examples': [], 'status': 'open'}
                clusters.append(c)
            for x in w:
                c['counts'][x] = c['counts'].get(x, 0) + 1
            c['top'] = [x for x, _ in sorted(c['counts'].items(), key=lambda kv: -kv[1])[:10]]
            c['uses'] += 1
            if s['id'] not in c['sessions']:
                c['sessions'].append(s['id'])
            c['examples'] = (c['examples'] + [{'text': p['text'][:300], 'actions': p['actions']}])[-6:]
    state['seen_prompts'] = sorted(seen)[-20000:]

    made = 0
    ready = [c for c in clusters if c['status'] == 'open'
             and (c['uses'] >= 20 or (c['uses'] >= 5 and len(c['sessions']) >= 2))]
    for c in sorted(ready, key=lambda c: -c['uses'])[:MAX_NEW_SKILLS]:
        examples = '\n\n'.join(f"REQUEST: {e['text']}\nACTIONS:\n" + '\n'.join(e['actions']) for e in c['examples'])
        try:
            r = ask_haiku(SKILL_PROMPT.format(uses=c['uses'], n_sessions=len(c['sessions']), examples=SECRET.sub('***', examples)))
        except (subprocess.SubprocessError, ValueError, OSError):
            break
        if not r or not r.get('worth'):
            c['status'] = 'not-a-skill'
            continue
        name = install_skill(r['name'], r.get('description', ''), r.get('steps', ''), set(r.get('keywords') or c['top'][:6]),
                             f"you asked for this {c['uses']} times in {len(c['sessions'])} sessions")
        c['status'], c['skill'] = 'skill', name
        made += 1
    return made


def inbox_candidates():
    """Distillation files candidates by name; one seen in 2+ sessions already has its recipe, so it becomes a skill."""
    inbox = VAULT / 'Inbox'
    for f in sorted(inbox.glob('*.md')) if inbox.exists() else []:
        text = f.read_text(encoding='utf-8', errors='ignore')
        n = len(re.findall(r'^\s*- session:', text, re.M))
        if n < 2 or 'status: skill' in text:
            continue
        name = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', f.stem)
        when = (re.search(r'\*\*When:\*\*\s*(.+)', text) or [None, ''])[1].strip()
        steps = (re.search(r'## Steps\n(.*?)(?=\n## |\Z)', text, re.S) or [None, ''])[1]
        if install_skill(name, when, steps, words(when + ' ' + name.replace('-', ' ')), f'it came up in {n} sessions'):
            f.write_text(text.replace('type: skill-candidate', 'type: skill-candidate\nstatus: skill', 1), encoding='utf-8')


def prune():
    stats = load(HOME / 'stats.json', {}).get('skills', {})
    kits = load(HOME / 'kits.json', {})
    for folder in LIB.iterdir() if LIB.exists() else []:
        md = folder / 'SKILL.md'
        if not md.exists() or 'created-by: helena' not in md.read_text(encoding='utf-8', errors='ignore'):
            continue
        last = stats.get(folder.name, {}).get('last') or time.strftime('%Y-%m-%d', time.localtime(md.stat().st_mtime))
        if (datetime.date.today() - datetime.date.fromisoformat(last[:10])).days > 30:
            shutil.rmtree(folder)
            kits.pop(f'auto:{folder.name}', None)
            news(f'Helena removed the skill "{folder.name}" she had created: nobody used it in 30 days.')
    save(HOME / 'kits.json', kits)
    cat = LIB / 'CATALOG.md'
    if cat.exists():  # drop catalog lines whose skill folder is gone
        lines = cat.read_text(encoding='utf-8').split('\n- **')
        keep = [lines[0]] + [l for l in lines[1:] if catalog_ok(l)]
        cat.write_text('\n- **'.join(keep), encoding='utf-8')


def catalog_ok(entry):  # a catalog entry whose SKILL.md still exists
    m = re.search(r'`([^`]+SKILL\.md)`', entry)
    return not m or pathlib.Path(m.group(1)).exists()


def main():
    stamp = HOME / 'worker.last'
    if '--now' not in sys.argv and stamp.exists() and time.time() - stamp.stat().st_mtime < 20 * 3600:
        return
    lock = HOME / 'worker.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime < 3600:
            return  # another run is going
        lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        HOME.mkdir(exist_ok=True)
        stamp.touch()
        all_sessions = list(sessions(days=30))
        profiles(plugin_catalog(), all_sessions)
        state = load(STATE, {})
        made = patterns(all_sessions, state)
        save(STATE, state)
        inbox_candidates()
        prune()
        print(f'{datetime.datetime.now():%Y-%m-%d %H:%M} worker ok: {len(all_sessions)} sessions, {made} new skill(s)')
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
