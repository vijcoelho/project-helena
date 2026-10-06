"""Tests the helena/hooks/guard.js hook (secrets and .helena/git rules) on real commit shapes, without calling Claude.

    python eval/test_guard.py
"""
import json, pathlib, subprocess, sys, tempfile

HOOK = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks' / 'guard.js'
KEY = 'sk_' + 'live_' + 'FAKE' * 6  # assembled here so this file does not trip secret scanners


def blocks(cmd, folder):
    r = subprocess.run(['node', str(HOOK)], input=json.dumps({'tool_input': {'command': cmd}, 'cwd': str(folder)}),
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def repo(tmp):
    d = pathlib.Path(tmp)
    git = lambda *a: subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *a], cwd=d, check=True, capture_output=True)
    (d / 'app.js').write_text('console.log(1)\n')
    git('init', '-q', '-b', 'main'); git('add', 'app.js'); git('commit', '-qm', 'init')
    return d, git


errors = []
with tempfile.TemporaryDirectory() as tmp:  # secrets
    d, git = repo(tmp)
    (d / '.env').write_text(f'STRIPE={KEY}\n')
    (d / 'config.js').write_text(f'module.exports = {{ k: "{KEY}" }}\n')
    (d / 'app.js').write_text('console.log(2)\n')
    cases = [
        ('git add app.js && git commit -m x', False),                                   # only the clean file
        ('git add -A && git commit -m x', True),                                        # would take .env
        ('git add . && git commit -m x', True),
        ('echo .env >> .gitignore && git add app.js .gitignore && git commit -m x', False),
        ('git add config.js && git commit -m x', True),                                 # key inside code
        ('git commit -am x', False),                                                    # -a skips untracked files
        ('git status', False),
    ]
    errors += [(c, want) for c, want in cases if blocks(c, d) != want]
    (d / 'app.js').write_text(f'const k = "{KEY}"\n')
    if not blocks('git commit -a -m x', d):
        errors.append(('git commit -a with a key in a tracked file', True))

for rules in ('main: no\nnever: *.mp4 renders/\n', 'main: não\nnunca: *.mp4 renders/\n'):  # English, and v0.4 Portuguese
    with tempfile.TemporaryDirectory() as tmp:
        d, git = repo(tmp)
        (d / '.helena').mkdir()
        (d / '.helena' / 'git').write_text(rules, encoding='utf-8')
        (d / 'app.js').write_text('console.log(2)\n')
        (d / 'demo.mp4').write_bytes(b'\0')
        (d / 'renders').mkdir(); (d / 'renders' / 'a.png').write_bytes(b'\0')
        cases = [
            ('git add app.js && git commit -m x', True),                                # straight to main
            ('git switch -c feat && git add app.js && git commit -m x', False),         # creates a branch in the same command
            ('git push', False),                                                        # pushing main is fine
        ]
        errors += [(c, want) for c, want in cases if blocks(c, d) != want]
        git('switch', '-qc', 'feat')
        cases = [
            ('git add app.js && git commit -m x', False),
            ('git add -A && git commit -m x', True),                                    # would take demo.mp4 and renders/
            ('git add renders/a.png && git commit -m x', True),
        ]
        errors += [(c, want) for c, want in cases if blocks(c, d) != want]

for c, want in errors:
    print(f"failed: {c} (expected: {'block' if want else 'allow'})")
print('ok' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
