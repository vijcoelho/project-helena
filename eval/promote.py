"""Promotes a skill candidate from the Obsidian Inbox/ to a benchmark task.

    python eval/promote.py                  # lists the candidates
    python eval/promote.py <name>           # creates ~/.helena/eval/tasks/<name>/ from the note

The note becomes the task's skeleton: prompt.md with the trigger, a check.py that still fails, an empty fixture/,
plugin/ with the skill, and ab.json comparing today's Helena (base) with Helena + the candidate.
You fill in prompt, fixture and check, run `python eval/run.py <name> -n 2`, and the skill only moves into
your setup if the helena column wins.
"""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'helena'))
from distill import VAULT  # noqa: E402

INBOX = VAULT / 'Inbox'
TASKS = pathlib.Path.home() / '.helena' / 'eval' / 'tasks'
DATE = r'^\d{4}-\d{2}-\d{2}-'


def section(text, title):
    m = re.search(rf'## {title}\n(.*?)(?=\n## |\Z)', text, re.S)
    return m.group(1).strip() if m else ''


def main():
    notes = sorted(INBOX.glob('*.md')) if INBOX.exists() else []
    if len(sys.argv) < 2:
        for n in notes:
            done = (TASKS / re.sub(DATE, '', n.stem)).exists()
            print(f"{'[already a task] ' if done else ''}{n.stem}")
        print(f'{len(notes)} candidate(s) in {INBOX}')
        return
    match = [n for n in notes if sys.argv[1] in n.stem]
    if len(match) != 1:
        sys.exit(f'{len(match)} notes match "{sys.argv[1]}": ' + ', '.join(n.stem for n in match))
    note = match[0]
    name = re.sub(DATE, '', note.stem)
    t = TASKS / name
    if t.exists():
        sys.exit(f'{t} already exists')
    text = note.read_text(encoding='utf-8')
    when = (re.search(r'\*\*When:\*\*\s*(.+)', text) or [None, ''])[1].strip()
    (t / 'fixture').mkdir(parents=True)
    # the candidate becomes a plugin of its own; base column = today's Helena, helena column = Helena + candidate
    skill = t / 'plugin' / 'skills' / name
    skill.mkdir(parents=True)
    (t / 'plugin' / '.claude-plugin').mkdir()
    (t / 'plugin' / '.claude-plugin' / 'plugin.json').write_text(json.dumps({'name': f'candidate-{name}'}), encoding='utf-8')
    (skill / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: {when}\n---\n\n{section(text, "Steps")}\n', encoding='utf-8')
    (t / 'ab.json').write_text(json.dumps({'base': ['--plugin-dir', '{helena}'],
                                           'helena': ['--plugin-dir', '{helena}', '--plugin-dir', '{task}/plugin']}), encoding='utf-8')
    (t / 'prompt.md').write_text(f'TODO: the request the way you would type it. Trigger from the note: {when}\n', encoding='utf-8')
    how = section(text, 'How to test').replace('\n', '\n# ')
    (t / 'check.py').write_text(
        f'# TODO: objective check. From the note:\n# {how}\nimport pathlib, sys\n'
        "d = pathlib.Path(sys.argv[1])\nprint('check not written yet')\nsys.exit(1)\n", encoding='utf-8')
    print(f'created {t}\nnext: prompt.md, fixture/, check.py (and review plugin/skills/{name}/SKILL.md); '
          f'then python eval/run.py {name} -n 2')


if __name__ == '__main__':
    main()
