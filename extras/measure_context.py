"""Measures how many tokens Claude Code spends before you type anything, and how much each enabled plugin weighs.

    python extras/measure_context.py

Opens one short Haiku session per plugin, so run it when your plan limit has room.
"""
import glob, json, os, re, shutil, subprocess, tempfile

CLAUDE = shutil.which('claude')
SETTINGS = os.path.expanduser('~/.claude/settings.json')


def tokens(settings):
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, 's.json')
        json.dump(settings, open(f, 'w'))
        r = subprocess.run([CLAUDE, '-p', '--output-format', 'json', '--no-session-persistence', '--model', 'haiku',
                            '--settings', f], input='ok', capture_output=True, text=True, encoding='utf-8', cwd=d)
        u = json.loads(r.stdout)['usage']
        return u['input_tokens'] + u['cache_creation_input_tokens'] + u['cache_read_input_tokens']


plugins = [p for p, on in json.load(open(SETTINGS, encoding='utf-8')).get('enabledPlugins', {}).items() if on]
uses = {}
for f in glob.glob(os.path.expanduser('~/.claude/projects/**/*.jsonl'), recursive=True):
    for m in re.finditer(r'"skill":"([^"]+)"', open(f, encoding='utf-8', errors='ignore').read()):
        uses[m.group(1)] = uses.get(m.group(1), 0) + 1

total = tokens({})
print(f'empty session today: {total} tokens\n')
print(f"{'plugin':45} {'tokens':>7} {'uses':>5}")
for p in plugins:
    without = tokens({'enabledPlugins': {p: False}})
    prefix = p.split('@')[0]
    n = sum(v for k, v in uses.items() if k.startswith(prefix))
    print(f'{p:45} {total - without:7} {n:5}')
