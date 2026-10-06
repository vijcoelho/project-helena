"""Tests the helena/hooks/trim.js hook (blocks context-flooding commands), without calling Claude.

    python eval/test_trim.py
"""
import json, pathlib, subprocess, sys, tempfile

HOOK = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks' / 'trim.js'


def blocks(tool, inp, folder):
    r = subprocess.run(['node', str(HOOK)], input=json.dumps({'tool_name': tool, 'tool_input': inp, 'cwd': str(folder)}),
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


with tempfile.TemporaryDirectory() as tmp:
    d = pathlib.Path(tmp)
    (d / 'node_modules').mkdir()
    (d / 'big.log').write_text('x' * 200_000)
    (d / 'small.js').write_text('console.log(1)\n')
    (d / 'package-lock.json').write_text('{}')
    cases = [
        ('Bash', {'command': 'cat big.log'}, True),
        ('Bash', {'command': 'cat big.log | tail -50'}, False),
        ('Bash', {'command': 'cat big.log  # helena:full'}, False),
        ('Bash', {'command': 'cat small.js'}, False),
        ('Bash', {'command': 'cat package-lock.json'}, True),
        ('Bash', {'command': 'git log'}, True),
        ('Bash', {'command': 'git log --oneline -20'}, False),
        ('Bash', {'command': 'git log -p -3'}, False),
        ('Bash', {'command': 'grep -rn foo .'}, True),
        ('Bash', {'command': 'grep -rn foo src --include=*.js'}, False),
        ('Bash', {'command': 'ls -R'}, True),
        ('Bash', {'command': 'npm test'}, False),
        ('PowerShell', {'command': 'Get-Content big.log'}, True),
        ('Read', {'file_path': str(d / 'big.log')}, True),
        ('Read', {'file_path': str(d / 'big.log'), 'limit': 100}, False),
        ('Read', {'file_path': str(d / 'package-lock.json')}, True),
        ('Read', {'file_path': str(d / 'dist' / 'app.min.js')}, True),
        ('Read', {'file_path': str(d / 'small.js')}, False),
    ]
    errors = [(t, i, want) for t, i, want in cases if blocks(t, i, d) != want]

for t, i, want in errors:
    print(f"failed: {t} {i} (expected: {'block' if want else 'allow'})")
print('ok' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
