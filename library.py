"""Helena's library: skills that do NOT load in every session, only when a kit or Helena calls for them.

    python library.py install https://github.com/greensock/gsap-skills   # clones and keeps every skill in the repo
    python library.py install <repo> --only semgrep,fp-check              # just some skills from the repo
    python library.py install <repo> --package                            # whole repo (skills that call each other by path)
    python library.py install ./some/local/folder                         # a local folder works too
    python library.py move my-skill       # takes it out of ~/.claude/skills (always loaded) into the library
    python library.py restore my-skill    # the opposite
    python library.py catalog             # rebuilds CATALOG.md

A skill in ~/.claude/skills costs context in EVERY session (its description goes into the prompt).
In the library it costs nothing until it is read.
"""
import pathlib, re, shutil, subprocess, sys, tempfile

LIB = pathlib.Path.home() / '.helena' / 'library'
GLOBAL = pathlib.Path.home() / '.claude' / 'skills'


def frontmatter(skill_md):
    text = skill_md.read_text(encoding='utf-8', errors='ignore')
    m = re.match(r'---\s*\n(.*?)\n---', text, re.S)
    fields = {}
    if m:
        for k in ('name', 'description'):
            v = re.search(rf'^{k}:\s*(.+?)(?=\n\w[\w-]*:|\Z)', m.group(1), re.S | re.M)
            if v:
                fields[k] = ' '.join(v.group(1).strip().strip('"\'>|-').split())
    return fields


def catalog():
    lines = ["# Helena's library catalog", '',
             'To use a skill: read its SKILL.md and follow it. Relative paths inside a skill start from its folder.', '']
    for md in sorted(LIB.rglob('SKILL.md')):
        if 'node_modules' in md.parts:
            continue
        f = frontmatter(md)
        desc = f.get('description', '')
        lines.append(f"- **{f.get('name') or md.parent.name}**: {desc[:120]}{'…' if len(desc) > 120 else ''}  \n  `{md.as_posix()}`")
    (LIB / 'CATALOG.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{len(lines) - 4} skills in the catalog: {LIB / "CATALOG.md"}')


def install(url, only=None, package=False):
    with tempfile.TemporaryDirectory() as tmp:
        if pathlib.Path(url).is_dir():
            shutil.copytree(url, tmp, dirs_exist_ok=True)
        else:
            subprocess.run(['git', '-c', 'core.longpaths=true', 'clone', '-q', '--depth', '1', url, tmp], check=True)
        if package:
            dest = LIB / url.rstrip('/').split('/')[-1].removesuffix('.git')
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(tmp, dest, ignore=shutil.ignore_patterns('.git', '.github', 'tests', 'evals'))
            print('  + package', dest.name)
            return
        for md in pathlib.Path(tmp).rglob('SKILL.md'):
            if '.git' in md.parts:
                continue
            name = frontmatter(md).get('name') or md.parent.name
            if only and name not in only:
                continue
            dest = LIB / name
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(md.parent, dest, ignore=shutil.ignore_patterns('.git'))
            print('  +', name)


def move(name, src, dst):
    origin = src / name
    if not (origin / 'SKILL.md').exists():
        sys.exit(f'{origin} has no SKILL.md')
    if (dst / name).exists():
        sys.exit(f'{dst / name} already exists')
    dst.mkdir(parents=True, exist_ok=True)
    shutil.move(str(origin), str(dst / name))
    print(f'{name}: {src} -> {dst}')


if __name__ == '__main__':
    cmd, *args = sys.argv[1:] or ['catalog']
    LIB.mkdir(parents=True, exist_ok=True)
    if cmd == 'install':
        only = next((a.split('=', 1)[1] if '=' in a else args[args.index(a) + 1] for a in args if a.startswith('--only')), None)
        targets = [a for a in args if not a.startswith('--') and a != only]
        for u in targets:
            install(u, only=set(only.split(',')) if only else None, package='--package' in args)
    elif cmd == 'move':
        for n in args:
            move(n, GLOBAL, LIB)
    elif cmd == 'restore':
        for n in args:
            move(n, LIB, GLOBAL)
    elif cmd != 'catalog':
        sys.exit(__doc__)
    catalog()
