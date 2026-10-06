"""The skills Helena created by herself: list them, or undo one (it is never recreated).

    python helena/skills.py            # list, with how often each was used
    python helena/skills.py undo <name>
    python helena/skills.py undo <name> learned   # drop the last "## Learned" line distill added to any library skill
    python helena/skills.py undo <name> fold      # restore the skill as it was before tidy.py folded its lessons in
"""
import json, pathlib, shutil, sys

HOME = pathlib.Path.home() / '.helena'
LIB = HOME / 'library'


def load(p, d):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return d


def mine():
    for md in sorted(LIB.glob('*/SKILL.md')):
        text = md.read_text(encoding='utf-8', errors='ignore')
        if 'created-by: helena' in text:
            desc = next((l[12:].strip() for l in text.splitlines() if l.startswith('description:')), '')
            yield md.parent.name, desc


def unlearn(name):
    md = LIB / name / 'SKILL.md'
    lines = md.read_text(encoding='utf-8').split('\n') if md.exists() else []
    if '## Learned' not in lines:
        sys.exit(f'"{name}" has nothing learned')
    start = lines.index('## Learned') + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith('## ')), len(lines))
    last = max((i for i in range(start, end) if lines[i].startswith('- ')), default=None)
    if last is None:
        sys.exit(f'"{name}" has nothing learned')
    gone = lines.pop(last)
    md.write_text('\n'.join(lines), encoding='utf-8')
    print(f'removed from {name}: {gone[2:]}')


def unfold(name):
    bak = LIB / name / 'SKILL.md.bak'
    if not bak.exists():
        sys.exit(f'"{name}" has no folded version to undo')
    bak.replace(LIB / name / 'SKILL.md')
    print(f'{name}: back to the version before the lessons were folded in')


def undo(name):
    folder = LIB / name
    if not (folder / 'SKILL.md').exists() or 'created-by: helena' not in (folder / 'SKILL.md').read_text(encoding='utf-8'):
        sys.exit(f'"{name}" is not a skill Helena created. Her skills: ' + ', '.join(n for n, _ in mine()))
    shutil.rmtree(folder)
    kits = load(HOME / 'kits.json', {})
    kits.pop(f'auto:{name}', None)
    (HOME / 'kits.json').write_text(json.dumps(kits, ensure_ascii=False, indent=1), encoding='utf-8')
    cat = LIB / 'CATALOG.md'
    if cat.exists():
        parts = cat.read_text(encoding='utf-8').split('\n- **')
        cat.write_text('\n- **'.join([parts[0]] + [p for p in parts[1:] if not p.startswith(f'{name}**')]), encoding='utf-8')
    state = load(HOME / 'patterns.json', {})
    for c in state.get('clusters', []):
        if c.get('skill') == name:
            c['status'] = 'rejected'  # the same requests will not turn into a skill again
    (HOME / 'patterns.json').write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'removed "{name}"; Helena will not create it again')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:2] == ['undo'] and sys.argv[3:4] == ['learned']:
        unlearn(sys.argv[2])
    elif sys.argv[1:2] == ['undo'] and sys.argv[3:4] == ['fold']:
        unfold(sys.argv[2])
    elif sys.argv[1:2] == ['undo'] and len(sys.argv) > 2:
        undo(sys.argv[2])
    else:
        stats = load(HOME / 'stats.json', {}).get('skills', {})
        rows = list(mine())
        for name, desc in rows:
            s = stats.get(name, {})
            print(f"- {name}: {desc}\n  used {s.get('uses', 0)}x, last {s.get('last', 'never')}  (remove: /helena:undo {name})")
        print(f'{len(rows)} skill(s) created by Helena' if rows else 'Helena has not created any skill yet.')
