"""Routines: prompts Helena runs by herself every so often, read-only and with a spending cap.

    python helena/routines.py                 # list
    python helena/routines.py add '<json>'    # {"name", "prompt", "every": "12h"|"1d"|"7d", "max_budget_usd": 0.1,
                                              #  "project": "<folder>", "goal": "<optional>"}
    python helena/routines.py remove <name>
    python helena/routines.py run <name>      # right now, ignoring "every"

The worker runs the due ones when a session ends (no scheduler, nothing always on), with Haiku.
A routine can only read (files and web). Anything that needs a decision becomes a "needs you" line in the vault
(Inbox/needs-you.md) and in the next session's brief; it is never acted on.
Every run is appended to Routines/<name>.md in the vault. A routine with a goal also logs its progress in Projects/<project>.md.
"""
import datetime, json, os, pathlib, re, shutil, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from history import HOME, ledger  # noqa: E402
from distill import LEAN, NO_WINDOW, SECRET, VAULT, slug, write  # noqa: E402
from worker import load, news, save  # noqa: E402

FILE = HOME / 'routines.json'
TOOLS = 'Read,Grep,Glob,WebSearch,WebFetch'  # read-only: a routine never changes anything
RULES = """

You are running unattended as a scheduled routine. You can only read; never try to change files or run commands.
{goal}When something needs a decision or an action from the user, do not do it: write one line per item starting with "NEEDS YOU:".
Keep the answer under 30 lines."""
GOAL = 'This routine works toward a goal: {goal}\nEnd with one line starting with "PROGRESS:" saying where the goal stands now.\n'


def seconds(every):
    m = re.fullmatch(r'(\d+)([hd])', str(every).strip())
    if not m or int(m[1]) < 1:
        raise ValueError(f'"every" must look like 12h or 7d, got {every!r}')
    return int(m[1]) * (3600 if m[2] == 'h' else 86400)


def run(r, routines):
    r['last'] = time.time()  # claimed before the slow call, so a second worker never runs it twice
    save(FILE, routines)
    cwd = r.get('project') or str(pathlib.Path.home())
    prompt = r['prompt'] + RULES.format(goal=GOAL.format(goal=r['goal']) if r.get('goal') else '')
    try:
        p = subprocess.run([shutil.which('claude') or 'claude', '-p', '--model', 'haiku', '--output-format', 'json',
                            '--tools', TOOLS, '--max-budget-usd', str(r.get('max_budget_usd', 0.1)), '--no-session-persistence', *LEAN],
                           input=prompt, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900,
                           env=dict(os.environ, HELENA_DISTILLING='1'), cwd=cwd, creationflags=NO_WINDOW)
        out = json.loads(p.stdout or '{}')
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        out = {'subtype': f'failed: {e}'}
    cost = out.get('total_cost_usd', 0)
    ledger({'what': f'routine:{r["name"]}', 'cost': cost})
    text = SECRET.sub('***', (out.get('result') or f"(no answer: {out.get('subtype', 'error')})").strip())
    now = datetime.datetime.now()

    note = VAULT / 'Routines' / f'{slug(r["name"])}.md'
    note.parent.mkdir(parents=True, exist_ok=True)
    head = '' if note.exists() else f'---\ntype: routine\ndescription: {r["prompt"][:100]}\n---\n# {r["name"]}\n'
    with open(note, 'a', encoding='utf-8') as f:
        f.write(f'{head}\n## {now:%Y-%m-%d %H:%M} (${cost:.3f})\n{text}\n')

    asks = re.findall(r'^\W*NEEDS YOU:\s*(.+)', text, re.M)
    if asks:
        inbox = VAULT / 'Inbox' / 'needs-you.md'
        inbox.parent.mkdir(parents=True, exist_ok=True)
        head = '' if inbox.exists() else '---\ntype: needs-you\ndescription: decisions routines left for the user\n---\n'
        with open(inbox, 'a', encoding='utf-8') as f:
            f.write(head + ''.join(f'- [ ] {now:%Y-%m-%d} {r["name"]}: {a}\n' for a in asks))
        news(f'Routine "{r["name"]}" needs you: ' + '; '.join(asks) + ' (vault Inbox/needs-you.md)')
    progress = re.search(r'^\W*PROGRESS:\s*(.+)', text, re.M)
    if r.get('goal') and r.get('project') and progress:
        write({'project': {'decisions': [f'routine {r["name"]}: {progress[1]}']}}, VAULT, 'routine', pathlib.Path(r['project']).name)
    return text


def run_due():
    routines = load(FILE, [])
    for r in routines:
        if time.time() - r.get('last', 0) >= seconds(r['every']):
            run(r, routines)
            print(f'{datetime.datetime.now():%Y-%m-%d %H:%M} routine {r["name"]} ran')


def main(args):
    routines = load(FILE, [])
    find = lambda name: next((r for r in routines if r['name'] == name), None)  # noqa: E731
    if args[:1] == ['add']:
        r = json.loads(args[1])
        r['name'] = slug(r['name'])
        seconds(r['every'])
        if not r.get('prompt'):
            raise ValueError('"prompt" is required')
        if r.get('project') and not os.path.isdir(r['project']):
            raise ValueError(f'project folder not found: {r["project"]}')
        save(FILE, [x for x in routines if x['name'] != r['name']] + [r])
        print(f'Routine "{r["name"]}" saved: every {r["every"]}, up to ${r.get("max_budget_usd", 0.1)} per run. '
              f'First run at the next session end.')
    elif args[:1] == ['remove'] and len(args) > 1:
        save(FILE, [r for r in routines if r['name'] != args[1]])
        print(f'Routine "{args[1]}" removed.' if find(args[1]) else f'No routine named "{args[1]}".')
    elif args[:1] == ['run'] and len(args) > 1:
        print(run(find(args[1]), routines) if find(args[1]) else f'No routine named "{args[1]}".')
    elif not routines:
        print('No routines yet. Example: /helena:routines every Monday check the dependencies of this project for updates')
    else:
        for r in routines:
            last = time.strftime('%Y-%m-%d %H:%M', time.localtime(r['last'])) if r.get('last') else 'never'
            print(f'- {r["name"]}: every {r["every"]}, up to ${r.get("max_budget_usd", 0.1)}, last run {last}'
                  + (f', project {pathlib.Path(r["project"]).name}' if r.get('project') else '')
                  + (f', goal: {r["goal"]}' if r.get('goal') else '') + f'\n  {r["prompt"][:150]}')


if __name__ == '__main__':
    main(sys.argv[1:])
