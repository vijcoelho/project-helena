"""What sits in the context before you type anything, piece by piece, and how often each piece was used.

    python helena/diet.py [days]            # the list (uses counted over the last 30 days by default)
    python helena/diet.py --off <plugin>    # turn a plugin off in this project only (.claude/settings.local.json)

Every skill, command and agent puts its name and description in the context of every message, used or not; a CLAUDE.md
goes in whole. This adds them up per plugin and per folder (4 characters ~ 1 token: an estimate, the measured total is
the "Fixed context" line of /helena:budget) and counts, from your own transcripts, how many times each was called.
The worker already turns off plugins a project never uses, except the ones with hooks; this shows those too, and your
own skills and agents, which nothing prunes. No LLM, nothing is changed without --off.
"""
import json, pathlib, re, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from worker import load, save  # noqa: E402

CLAUDE = pathlib.Path.home() / '.claude'
tok = lambda chars: round(chars / 4)
k = lambda n: f'{n / 1000:.1f}k' if n >= 1000 else str(n)


def described(folder, pattern):
    """[(name, characters its listing takes)] for the skills, commands or agents under a folder."""
    out = []
    for f in sorted(folder.glob(pattern)) if folder.is_dir() else []:
        head = f.read_text(encoding='utf-8', errors='ignore')[:3000]
        if re.search(r'^disable-model-invocation:\s*true', head, re.M):
            continue  # not listed to the model: costs nothing until the user types it
        desc = (re.search(r'^description:\s*(.+)$', head, re.M) or [None, ''])[1]
        name = (re.search(r'^name:\s*(.+)$', head, re.M) or [None, f.parent.name if f.name == 'SKILL.md' else f.stem])[1].strip()
        out.append((name, len(name) + len(desc) + 8))
    return out


def pieces(cwd):
    settings, local = load(CLAUDE / 'settings.json', {}), load(cwd / '.claude' / 'settings.local.json', {})
    installed = load(CLAUDE / 'plugins' / 'installed_plugins.json', {}).get('plugins', {})
    on = {**settings.get('enabledPlugins', {}), **load(cwd / '.claude' / 'settings.json', {}).get('enabledPlugins', {}), **local.get('enabledPlugins', {})}
    for key, enabled in on.items():
        root = pathlib.Path((installed.get(key) or [{}])[0].get('installPath', ''))
        if not enabled or not root.is_dir():
            continue
        parts = {'skills': described(root / 'skills', '*/SKILL.md'), 'commands': described(root / 'commands', '*.md'), 'agents': described(root / 'agents', '*.md')}
        hooks = (root / 'hooks' / 'hooks.json').exists() or 'hooks' in load(root / '.claude-plugin' / 'plugin.json', {})
        yield {'kind': 'plugin', 'key': key, 'name': key.split('@')[0], 'hooks': hooks, 'parts': parts,
               'chars': sum(c for p in parts.values() for _, c in p)}
    for label, base in (('yours (~/.claude)', CLAUDE), ('this project (.claude)', cwd / '.claude')):
        parts = {'skills': described(base / 'skills', '*/SKILL.md'), 'commands': described(base / 'commands', '*.md'), 'agents': described(base / 'agents', '*.md')}
        if any(parts.values()):
            yield {'kind': 'folder', 'name': label, 'parts': parts, 'chars': sum(c for p in parts.values() for _, c in p)}
    for f in (CLAUDE / 'CLAUDE.md', cwd / 'CLAUDE.md', cwd / 'AGENTS.md'):
        if f.is_file():
            yield {'kind': 'file', 'name': str(f).replace(str(pathlib.Path.home()), '~'), 'parts': {}, 'chars': f.stat().st_size}


def uses(days):
    """How many times each skill and agent type was called, from the transcripts changed in the last `days`."""
    n, since = {}, time.time() - days * 86400
    for f in (CLAUDE / 'projects').glob('**/*.jsonl'):
        if f.stat().st_mtime < since:
            continue
        for m in re.finditer(r'"(?:skill|subagent_type)":"([^"]+)"', f.read_text(encoding='utf-8', errors='ignore')):
            n[m.group(1)] = n.get(m.group(1), 0) + 1
    return n


PROHIBIT = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\W*(?:don[’']t|do not|never|avoid|não|nunca|jamais|evite)\b", re.I)
TREE = re.compile(r'├──|└──|│')


def runs(lines, hit, n):
    """[(first, last)] 1-based, for each run of at least n consecutive lines where hit(line)."""
    out, i = [], 0
    while i < len(lines):
        j = i
        while j < len(lines) and hit(lines[j]):
            j += 1
        if j - i >= n:
            out.append((i + 1, j))
        i = max(j, i + 1)
    return out


def lint(cwd):
    """Per instruction file: [(first line, last line, tokens, what, hint)] for what the repo already shows. Reports only."""
    scripts = load(cwd / 'package.json', {}).get('scripts', {})
    restates = lambda l: any(cmd in l and re.search(rf'\b(?:npm|pnpm|yarn|bun)(?: run)? {re.escape(n)}\b', l) for n, cmd in scripts.items() if cmd)
    for name in ('CLAUDE.md', 'AGENTS.md'):
        f = cwd / name
        if not f.is_file():
            continue
        lines = f.read_text(encoding='utf-8', errors='ignore').splitlines()
        found = [(a, b, 'npm script', '(package.json already says it)') for a, b in runs(lines, restates, 1)]
        found += [(a, b, 'directory tree', '(the repo shows it)') for a, b in runs(lines, TREE.search, 4)]
        found += [(a, b, 'prohibition list', '(a long "do not" list is followed less than three positive rules)') for a, b in runs(lines, PROHIBIT.search, 8)]
        rows = [(a, b, tok(sum(len(l) + 1 for l in lines[a - 1:b])), what, hint) for a, b, what, hint in found]
        if rows:
            yield name, rows


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    cwd = pathlib.Path.cwd()
    if sys.argv[1:2] == ['--off']:
        want = sys.argv[2] if len(sys.argv) > 2 else ''
        key = next((p['key'] for p in pieces(cwd) if p['kind'] == 'plugin' and want in (p['key'], p['name'])), None)
        if not key:
            sys.exit(f'no enabled plugin named {want!r} here')
        f = cwd / '.claude' / 'settings.local.json'
        s = load(f, {})
        s.setdefault('enabledPlugins', {})[key] = False
        f.parent.mkdir(exist_ok=True)
        save(f, s)
        print(f'{key} is off in this project ({f}). It applies from the next session; delete that line to turn it back on.')
        return
    days = int(sys.argv[1]) if sys.argv[1:] and sys.argv[1].isdigit() else 30
    used, rows, total = uses(days), [], 0
    for p in pieces(cwd):
        names = [n for part in p['parts'].values() for n, _ in part]
        count = sum(used.get(n, 0) + (used.get(f"{p['name']}:{n}", 0) if p['kind'] == 'plugin' else 0) for n in names)
        idle = [n for n in names if not used.get(n) and not used.get(f"{p['name']}:{n}")]
        what = ', '.join(f'{len(v)} {w}' for w, v in p['parts'].items() if v)
        note = ''
        if p['kind'] == 'plugin':
            note = ' [has hooks: it works without being called]' if p['hooks'] else \
                f'  -> never called: python helena/diet.py --off {p["name"]}' if not count else ''
        elif p['kind'] == 'folder' and idle:
            note = f'  -> never called ({len(idle)}): ' + ', '.join(idle[:6]) + (' …' if len(idle) > 6 else '')
        elif p['kind'] == 'file' and p['chars'] > 12000:
            note = '  -> over ~3k tokens: rules that only matter sometimes cost less as memory notes'
        rows.append((tok(p['chars']), '-' if p['kind'] == 'file' else str(count), f"{p['kind']} {p['name']}" + (f': {what}' if what else ''), note))
        total += tok(p['chars'])
    print(f'In the context before you type, re-read on every message (estimate: descriptions, 4 characters ~ 1 token; uses in {days} days)')
    print(f"  {'~tokens':>7} {'uses':>5}  piece")
    for t, c, name, note in sorted(rows, reverse=True):
        if t >= 20:
            print(f'  {k(t):>7} {c:>5}  {name}{note}')
    print(f'  {k(total):>7}        listed here. The rest of the fixed context is the CLI itself (system prompt, tool definitions) and MCP servers.')
    print('--off turns a plugin off in this folder only; deleting its line from .claude/settings.local.json turns it back on.')
    for name, rows in lint(cwd):
        print(f'\n{name}: ~{sum(r[2] for r in rows)} tokens could go (paid on every call):')
        for a, b, t, what, hint in rows:
            print(f'  lines {a}-{b}: {what}, ~{t} tokens {hint}')


if __name__ == '__main__':
    main()
