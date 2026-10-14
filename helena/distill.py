"""Distills a Claude Code (or Codex) session: what is worth remembering goes to Obsidian, what looks like a skill goes to the Inbox.

    python helena/distill.py <transcript.jsonl> [vault]
    python helena/distill.py --backfill [n]      # your last n project sessions (default 10), for /helena:setup
    echo {"memories": [...]} | python helena/distill.py --remember <source>   # helena-mcp writes a note

Runs by itself in the background, on Haiku: every 6 prompts (router.js checkpoint) and at SessionEnd.
Each run only reads the turns after the last one (offset per transcript in ~/.helena/distilled.json).
Memory is written right away; a skill never is: it waits in the Inbox until it wins a benchmark task.
When a library skill was used and the user corrected the result, the lesson lands under "## Learned" in its SKILL.md.
"""
import datetime, json, os, pathlib, re, shutil, subprocess, sys

_CONF = pathlib.Path.home() / '.helena' / 'vault'  # one line: path of the Obsidian vault
VAULT = pathlib.Path(os.environ.get('HELENA_VAULT') or (_CONF.read_text().strip() if _CONF.exists() else '')
                     or pathlib.Path.home() / 'Helena')
SECRET = re.compile(r'\b(sk[_-][A-Za-z0-9_-]{16,}|[a-f0-9]{40,}|(pk|rk)_(live|test)_[A-Za-z0-9]{10,}|'
                    r'AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|\d{8,}:[A-Za-z0-9_-]{30,}|'
                    r'(AKIA|ASIA)[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{10,})')
MAX_CHARS = 30000
# runs with no console (detached from the hook): without this, Windows opens a visible window for claude.exe and git
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
MIN_TURNS = 4
HOME = pathlib.Path.home() / '.helena'
STATE = HOME / 'distilled.json'  # transcript path -> number of turns already distilled
LIB = HOME / 'library'
USED = re.compile(r'\.helena[\\/]+library[\\/]+([\w.-]+)[\\/]+SKILL\.md')

PROMPT = """You read a session between a user and an AI coding assistant and extract what is worth remembering six months from now.

SAVE (memories):
- a correction the user made ("no, use X", "stop doing Y", "actually it works like this"), with the why
- a preference or work rule of theirs that holds for other sessions
- a project decision and its why; a real constraint (technical, deadline, money, legal)
- a durable fact about a project (stack, where it runs, how it deploys)

DO NOT SAVE: what only mattered for this task, what can be read in the code or in git, secrets/keys/passwords, the obvious.

SKILL CANDIDATE: only if the session shows a multi-step procedure the user will ask for again and that the AI
had to learn the hard way (trial and error, correction). Say how to test whether the skill works.

PROJECT ({project}): if the session changed something durable about this project, say what it is like NOW in 1-3 lines
(not a list of edits; the code and git already have those) and the decisions taken, each with its why.

Write every note in the language the user writes in. A memory that only applies to this project gets "project": "{project}";
one that holds everywhere gets "project": "".
When a fact depends on code that can change, put in "checks" the files (or "file#Name" for a function, class or setting
inside a file) that must still exist for it to hold, with paths relative to the project folder; Helena flags the note when they go.
When a new fact REPLACES an existing memory (moved from X to Y, a rule that changed), write a NEW slug and put the old
slug in "supersedes": the old note is archived. Never append a contradicting fact to the old note.

Memories that already exist (slug: description). If it is the same thing, use the SAME slug to add to it:
{index}

Answer ONLY with JSON, no text around it:
{{"memories": [{{"slug": "kebab-case", "type": "rule|preference|fact|user", "description": "one line",
  "body": "short markdown", "links": ["related-slug"], "project": "", "checks": "src/x.js, src/y.py#Name", "supersedes": []}}],
 "skills": [{{"name": "kebab-case", "when": "trigger", "steps": "markdown", "how_to_test": "task + objective check"}}],
 "project": {{"state": "", "decisions": []}}}}
An empty list is the right answer when nothing is durable. When in doubt, do not save.
{learned}
SESSION:
{session}"""


def turns(transcript):
    parts = []
    for line in open(transcript, encoding='utf-8', errors='ignore'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        c = (d.get('message') or {}).get('content')
        p = d.get('payload') or {}
        if d.get('type') == 'response_item' and p.get('type') == 'message':  # Codex rollout (~/.codex/sessions)
            text = ' '.join(b.get('text', '') for b in p.get('content') or []).strip()
            if p.get('role') == 'user' and text and not text.startswith(('<', '# AGENTS.md')):
                parts.append('USER: ' + text)
            elif p.get('role') == 'assistant' and text:
                parts.append('AI: ' + text[:1500])
        elif d.get('type') == 'user' and isinstance(c, str) and not c.startswith('<'):
            parts.append('USER: ' + c.strip())
        elif d.get('type') == 'assistant' and isinstance(c, list):
            text = ' '.join(b.get('text', '') for b in c if b.get('type') == 'text').strip()
            if text:
                parts.append('AI: ' + text[:1500])
    return parts


def used_skills(transcript):
    """Library skills the assistant opened this session (its own tool calls, not paths the hooks merely listed)."""
    names = set()
    for line in open(transcript, encoding='utf-8', errors='ignore'):
        if ('"assistant"' in line or 'tool_call"' in line) and 'library' in line:
            names |= {n for n in USED.findall(line) if (LIB / n / 'SKILL.md').exists()}
    return sorted(names)


LEARNED = """
SKILLS USED THIS SESSION: {names}. If the user corrected or improved work done with one of them, add to the JSON
"learned": [{{"skill": "one of those names", "lesson": "one line, imperative, reusable next time"}}]. Only real corrections.
"""


def index(memory):
    lines = []
    for f in sorted(memory.glob('*.md')):
        m = re.search(r'^description:\s*(.+)$', f.read_text(encoding='utf-8', errors='ignore'), re.M)
        lines.append(f'- {f.stem}: {m.group(1) if m else ""}')
    return '\n'.join(lines) or '(none)'


# no plugins, skills or MCP in Helena's own calls: ~4x cheaper per turn (measured $0.087 -> $0.022 for "say ok")
LEAN = ['--strict-mcp-config', '--disable-slash-commands', '--setting-sources', 'project']


def ask(prompt, what='distill'):
    """One Haiku call with no tools; returns the JSON object in its answer (None when there is none)."""
    claude = shutil.which('claude') or 'claude'
    r = subprocess.run([claude, '-p', '--model', 'haiku', '--output-format', 'json', '--tools', '',
                        '--no-session-persistence', *LEAN], input=prompt, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=300,
                       env=dict(os.environ, HELENA_DISTILLING='1'), cwd=pathlib.Path.home(), creationflags=NO_WINDOW)
    if not r.stdout.strip():  # empty answer: say why (it lands in the log) instead of a bare JSON error
        raise ValueError(f'claude -p returned nothing (exit {r.returncode}): {r.stderr.strip()[-500:]}')
    out = json.loads(r.stdout)
    u = out.get('usage') or {}
    with open(HOME / 'ledger.jsonl', 'a', encoding='utf-8') as f:  # Helena's own spending
        f.write(json.dumps({'ts': datetime.datetime.now().isoformat(timespec='seconds'), 'what': what,
                            'cost': out.get('total_cost_usd', 0), 'tokens': sum(u.get(x, 0) for x in (
                                'input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'))}) + '\n')
    m = re.search(r'\{.*\}', out.get('result', ''), re.S)
    return json.loads(m.group(0)) if m else None


def slug(s):
    return re.sub(r'[^a-z0-9-]+', '-', s.lower()).strip('-')[:60] or 'note'


def write(data, vault, source, project='', commits='', used=()):
    memory, inbox, projects = vault / 'Memory', vault / 'Inbox', vault / 'Projects'
    for d in (memory, inbox, projects):
        d.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    done = []
    for m in data.get('memories', []):
        f = memory / f"{slug(m['slug'])}.md"
        links = ', '.join(f'[[{slug(l)}]]' for l in m.get('links', []))
        body = SECRET.sub('***', m.get('body', '').strip())
        old = m.get('supersedes') or []
        for s in (old.split(',') if isinstance(old, str) else old):  # the fact it replaces leaves Memory, kept in Archive
            gone = memory / f'{slug(s)}.md'
            if s.strip() and gone.exists() and gone != f:
                (vault / 'Archive').mkdir(exist_ok=True)
                shutil.move(gone, vault / 'Archive' / gone.name)
                with open(vault / 'Archive' / gone.name, 'a', encoding='utf-8') as a:
                    a.write(f'\nSuperseded by [[{f.stem}]] on {today}.\n')
                done.append(vault / 'Archive' / gone.name)
        if f.exists():
            f.write_text(f.read_text(encoding='utf-8').rstrip() + f'\n\n## {today}\n{body}\n', encoding='utf-8')
        else:
            scope = f"project: {m['project']}\n" if m.get('project') else ''
            extra = ''.join(k + ': ' + ' '.join(str(m[k]).split()) + '\n' for k in ('checks', 'until') if m.get(k))
            f.write_text(f"---\ntype: {m.get('type', 'fact')}\ndescription: {SECRET.sub('***', m['description'])}\n"
                         f"{scope}{extra}source: {source}\n---\n{body}\n" +
                         (f'\nRelated: {links}\n' if links else '') + (f'\nProject: [[{project}]]\n' if m.get('project') else ''),
                         encoding='utf-8')
        done.append(f)
    for s in data.get('skills', []):
        # one note per candidate; every session that shows it again adds a line, and 2+ sessions turn it into a skill
        f = inbox / f"{slug(s['name'])}.md"
        line = f'- session: {source} ({today})\n'
        if f.exists():
            f.write_text(f.read_text(encoding='utf-8').rstrip() + '\n' + line, encoding='utf-8')
        else:
            f.write_text(SECRET.sub('***', f"---\ntype: skill-candidate\n---\n# {s['name']}\n\n"
                         f"**When:** {s.get('when', '')}\n\n## Steps\n{s.get('steps', '')}\n\n"
                         f"## How to test\n{s.get('how_to_test', '')}\n\n## Sessions\n{line}"), encoding='utf-8')
        done.append(f)
    for l in data.get('learned', []):
        f = LIB / slug(l.get('skill', '')) / 'SKILL.md'
        if l.get('skill') in used and f.exists() and l.get('lesson'):
            learn(f, f"- {today}: {SECRET.sub('***', l['lesson'].strip())}")
            done.append(f)
    p = data.get('project') or {}
    if project and (p.get('state') or p.get('decisions') or commits):
        # the project's hub note: what it is like now (replaced) + decisions and commits (appended)
        f = projects / f'{project}.md'
        old = f.read_text(encoding='utf-8') if f.exists() else f'---\ntype: project\ndescription: hub of {project}\n---\n# {project}\n\n## Now\n\n## Log\n'
        if p.get('state'):
            old = re.sub(r'## Now\n.*?(?=\n## Log)', f"## Now\n{SECRET.sub('***', p['state'].strip())}\n", old, flags=re.S)
        entry = ''.join(f'- {SECRET.sub("***", d)}\n' for d in p.get('decisions', [])) + (f'- commits:\n{commits}' if commits else '')
        if entry:
            old = old.rstrip() + f'\n\n### {today}\n{entry}'
        f.write_text(old + '\n', encoding='utf-8')
        done.append(f)
    return done


def learn(skill_md, line):
    """Appends a line at the end of the skill's "## Learned" section (created at the bottom when missing)."""
    text = skill_md.read_text(encoding='utf-8').rstrip('\n') + '\n'
    if '\n## Learned\n' not in text:
        text += '\n## Learned\n'
    head, tail = text.split('\n## Learned\n', 1)
    body, sep, rest = tail.partition('\n## ')
    body = body.strip('\n')
    skill_md.write_text(f'{head}\n## Learned\n' + (body + '\n' if body else '') + line + '\n' + (f'\n## {rest}' if sep else ''),
                        encoding='utf-8')


def project_of(transcript):
    """Folder the session ran in, and the commits made there during the session (no LLM: plain git)."""
    cwd = started = None
    for line in open(transcript, encoding='utf-8', errors='ignore'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        cwd, started = cwd or d.get('cwd') or (d.get('payload') or {}).get('cwd'), started or d.get('timestamp')
        if cwd and started:
            break
    if not cwd or not os.path.isdir(cwd) or pathlib.Path(cwd) == pathlib.Path.home():
        return '', ''
    try:
        log = subprocess.run(['git', 'log', '--oneline', '-15', f'--since={started}'], cwd=cwd, capture_output=True,
                             text=True, encoding='utf-8', errors='replace', timeout=10, creationflags=NO_WINDOW).stdout
    except (OSError, subprocess.SubprocessError):
        log = ''
    return pathlib.Path(cwd).name, ''.join(f'  - {l}\n' for l in log.splitlines())


def main():
    if sys.argv[1] == '--remember':  # helena-mcp: {"memories": [...]} on stdin, written like a distill would
        for f in write(json.load(sys.stdin), VAULT, sys.argv[2] if len(sys.argv) > 2 else 'mcp'):
            print(f)
        return
    if sys.argv[1] == '--backfill':
        return backfill(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    try:
        distill(sys.argv[1], pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else VAULT)
    except (ValueError, OSError, subprocess.SubprocessError) as e:
        sys.exit(f'{datetime.datetime.now():%Y-%m-%d %H:%M} {e}')


def backfill(n):
    """/helena:setup: distills your last n project sessions, so a fresh Helena starts knowing how you work."""
    import glob
    done = 0
    for f in sorted(glob.glob(str(pathlib.Path.home() / '.claude' / 'projects' / '*' / '*.jsonl')), key=os.path.getmtime, reverse=True):
        if done >= n:
            break
        if not project_of(f)[0]:
            continue  # ponytail: skips sessions in the home folder and in deleted (temp/benchmark) folders alike
        try:
            if distill(f, VAULT):
                done += 1
                print(f'{done}/{n} {pathlib.Path(f).stem}', flush=True)
        except (ValueError, OSError, subprocess.SubprocessError) as e:
            print(f'skipped {pathlib.Path(f).stem}: {e}', flush=True)
    print(f'done: {done} session(s) distilled into {VAULT}')


def distill(transcript, vault):
    """Returns True when it called the LLM (the session had new turns worth reading)."""
    parts = turns(transcript)
    if sum(p.startswith('USER:') for p in parts) < MIN_TURNS:  # short sessions rarely teach anything; saves the plan limit
        return False
    # claim the new turns before the slow LLM call, so a checkpoint and SessionEnd never distill the same turns twice
    # ponytail: a failed call loses its turns; keep the offset until success if that ever matters
    state = {k: v for k, v in json.loads(STATE.read_text() if STATE.exists() else '{}').items() if os.path.exists(k)}
    key = str(pathlib.Path(transcript).resolve())
    new, state[key] = parts[state.get(key, 0):], len(parts)
    if not any(p.startswith('USER:') for p in new):
        return False
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))
    text = SECRET.sub('***', '\n\n'.join(new))[-MAX_CHARS:]
    project, commits = project_of(transcript)
    used = used_skills(transcript)
    data = ask(PROMPT.format(index=index(vault / 'Memory'), session=text, project=project or 'none',
                             learned=LEARNED.format(names=', '.join(used)) if used else '')) or {}
    for f in write(data, vault, pathlib.Path(transcript).stem, project, commits, used):
        print(f)
    return True


if __name__ == '__main__':
    main()
