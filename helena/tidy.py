"""Helena tidies what she learned. Run by the worker (at most once every 20 hours); `python helena/tidy.py` runs it now.

1. Memory hygiene: Haiku reads the memory notes and merges duplicates or contradictions into one note; the merged-away
   notes and the kept note's previous version move to <vault>/Archive/ (move them back to undo). Notes that look outdated
   are only flagged in the next session's news. Runs only when a memory note changed since the last time.
2. Skills that tidy themselves: a library skill with 5+ "## Learned" lines gets them folded into its recipe by Haiku,
   so it stays short. The previous version is kept as SKILL.md.bak (`/helena:undo <skill> fold` restores it).
3. Weekly review, no LLM: <vault>/Weekly/<year>-W<week>.md with what changed in 7 days, open "needs you" and Helena's cost.
"""
import datetime, json, pathlib, re, shutil, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from distill import LIB, SECRET, VAULT, ask, slug  # noqa: E402
from worker import HOME, load, news, save  # noqa: E402

STATE = HOME / 'tidy.json'
FOLD_AT = 5
MAX_CHARS = 60000

MERGE = """Below are the notes of a user's memory, one block each, with the date each was last changed.
Find notes that say the same thing or contradict each other. Never group notes with a different "project:".
For each group write ONE merged note that keeps every fact that is still true (in a contradiction, the newer note wins).
Also list notes that look outdated (a plan that already happened, a version that moved on). Leave fine notes alone.
Write a merged note in the language of the note you keep. Answer ONLY with JSON:
{{"merge": [{{"keep": "slug", "drop": ["slug"], "description": "one line", "body": "markdown, no frontmatter"}}],
 "stale": [{{"slug": "slug", "why": "one line"}}]}}
Empty lists are the right answer when everything is fine.

NOTES:
{notes}"""

FOLD = """Below is a skill (a recipe an AI assistant reads before a task). Its "## Learned" section has lessons from the
user's corrections. Rewrite the skill so each lesson lives in the right place of the recipe, and remove the "## Learned"
section. Keep everything else that is still right, the headings and the language. Add nothing new. Answer ONLY with JSON:
{{"skill": "the full new markdown"}}

SKILL:
{skill}"""


def newest(folder):
    return max((f.stat().st_mtime for f in folder.glob('*.md')), default=0)


def hygiene(vault, state):
    memory, archive = vault / 'Memory', vault / 'Archive'
    notes = sorted(memory.glob('*.md')) if memory.exists() else []
    if len(notes) < 2 or newest(memory) <= state.get('memory', 0):
        return
    blocks = '\n\n'.join(f'=== {f.stem} ({time.strftime("%Y-%m-%d", time.localtime(f.stat().st_mtime))})\n'
                         + f.read_text(encoding='utf-8', errors='ignore')[:3000] for f in notes)
    data = ask(MERGE.format(notes=SECRET.sub('***', blocks)[:MAX_CHARS]), 'tidy-memory') or {}
    today = datetime.date.today().isoformat()
    for m in data.get('merge', []):
        keep = memory / f"{slug(m.get('keep', ''))}.md"
        drops = [memory / f'{slug(d)}.md' for d in m.get('drop', [])]
        drops = [d for d in drops if d.exists() and d != keep]
        if not keep.exists() or not drops or not m.get('body'):
            continue
        archive.mkdir(parents=True, exist_ok=True)
        old = keep.read_text(encoding='utf-8')
        shutil.copy(keep, archive / f'{today}-{keep.name}')
        front = (re.match(r'---\n(.*?)\n---\n', old, re.S) or [None, f'type: fact\ndescription: {m.get("description", "")}'])[1]
        if m.get('description'):
            front = re.sub(r'^description:.*$', lambda _: f"description: {m['description']}", front, flags=re.M)
        keep.write_text(f"---\n{front}\n---\n{SECRET.sub('***', m['body'].strip())}\n\nMerged on {today}: "
                        + ', '.join(d.stem for d in drops) + '\n', encoding='utf-8')
        for d in drops:
            shutil.move(d, archive / f'{today}-{d.name}')
        for f in memory.glob('*.md'):  # links to a merged-away note now point to the kept one
            text = f.read_text(encoding='utf-8')
            new = text
            for d in drops:
                new = new.replace(f'[[{d.stem}]]', f'[[{keep.stem}]]')
            if new != text:
                f.write_text(new, encoding='utf-8')
        news(f'Helena merged the memory notes {", ".join(d.stem for d in drops)} into "{keep.stem}". '
             f'Previous versions are in the vault Archive/ folder.')
    for s in data.get('stale', []):
        if (memory / f"{slug(s.get('slug', ''))}.md").exists():
            news(f'The memory "{slug(s["slug"])}" may be outdated ({s.get("why", "")}). If so: /helena:forget {slug(s["slug"])}')
    state['memory'] = newest(memory)


def learned_lines(text):
    section = re.search(r'\n## Learned\n(.*?)(?=\n## |\Z)', text, re.S)
    return re.findall(r'^- .+', section.group(1), re.M) if section else []


def fold(lib):
    for md in sorted(lib.glob('*/SKILL.md')) if lib.exists() else []:
        text = md.read_text(encoding='utf-8')
        if len(learned_lines(text)) < FOLD_AT:
            continue
        m = re.match(r'(---\n.*?\n---\n)(.*)', text, re.S)
        front, body = (m[1], m[2]) if m else ('', text)
        new = ((ask(FOLD.format(skill=body), 'tidy-skill') or {}).get('skill') or '').strip()
        if not new or '\n## Learned\n' in f'\n{new}\n':
            continue  # no answer, or the lessons were not folded: keep the skill as it is
        shutil.copy(md, md.with_name('SKILL.md.bak'))
        md.write_text(f'{front}{new}\n', encoding='utf-8')
        news(f'Helena folded the lessons of the skill "{md.parent.name}" into its recipe. '
             f'Undo: /helena:undo {md.parent.name} fold')


def weekly(vault, lib):
    today = datetime.date.today()
    year, week, _ = today.isocalendar()
    since, start = time.time() - 7 * 86400, (today - datetime.timedelta(days=7)).isoformat()
    changed = [f.stem for f in sorted((vault / 'Memory').glob('*.md')) if f.stat().st_mtime > since]
    lessons, created = [], []
    for md in sorted(lib.glob('*/SKILL.md')) if lib.exists() else []:
        text = md.read_text(encoding='utf-8', errors='ignore')
        bak = md.with_name('SKILL.md.bak')  # lessons folded in this week only remain in the backup
        for l in learned_lines(text) + (learned_lines(bak.read_text(encoding='utf-8')) if bak.exists() else []):
            if l[2:12] >= start and f'{md.parent.name}: {l[2:]}' not in lessons:
                lessons.append(f'{md.parent.name}: {l[2:]}')
        when = re.search(r'^created:\s*(\S+)', text, re.M)
        if 'created-by: helena' in text and when and when[1] >= start:
            created.append(md.parent.name)
    needs = vault / 'Inbox' / 'needs-you.md'
    open_items = re.findall(r'^- \[ \] (.+)', needs.read_text(encoding='utf-8')) if needs.exists() else []
    ledger = HOME / 'ledger.jsonl'
    cost = sum(e.get('cost', 0) for e in map(json.loads, ledger.read_text(encoding='utf-8').splitlines())
               if e.get('ts', '') >= start) if ledger.exists() else 0
    item = lambda xs: ''.join(f'- {x}\n' for x in xs) or '- nothing\n'  # noqa: E731
    out = vault / 'Weekly' / f'{year}-W{week:02d}.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f'---\ntype: weekly\ndescription: what Helena learned in the 7 days up to {today}\n---\n'
                   f'# Week {week}, {year}\n\n## Memory notes new or changed\n{item(f"[[{c}]]" for c in changed)}\n'
                   f'## Skills created\n{item(created)}\n## Lessons learned by skills\n{item(lessons)}\n'
                   f'## Needs you\n{item(open_items)}\n## Helena\'s cost\n- ${cost:.2f} in 7 days. Your own tokens: /helena:budget\n',
                   encoding='utf-8')
    return out


def main(vault=VAULT, lib=LIB):
    state = load(STATE, {})
    for step in (lambda: hygiene(vault, state), lambda: fold(lib)):
        try:
            step()
        except (ValueError, OSError, subprocess.SubprocessError) as e:
            print(f'tidy: {e}')
    save(STATE, state)
    return weekly(vault, lib)


if __name__ == '__main__':
    print(main())
