"""Tests the helena/hooks/guard.js hook (secrets and .helena/git rules) on real commit shapes, without calling Claude.

    python eval/test_guard.py
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile

HOOK = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks' / 'guard.js'
KEY = 'sk_' + 'live_' + 'FAKE' * 6  # assembled here so this file does not trip secret scanners
HOME = tempfile.mkdtemp()  # the hook logs every block: keep the test's out of the real ~/.helena/audit.jsonl


AWS = 'AKIA' + 'IOSFODNN7' + 'EXAMPLE'                # assembled: no key-shaped literal in the source
SLACK = 'xox' + 'b-' + '1234567890-abcdefghij'
TOOLS = os.pathsep.join(os.path.dirname(shutil.which(t)) for t in ('node', 'git'))  # PATH with no gitleaks, even if one is installed


def blocks(cmd, folder, path=TOOLS):
    r = subprocess.run(['node', str(HOOK)], input=json.dumps({'tool_input': {'command': cmd}, 'cwd': str(folder)}),
                       capture_output=True, text=True, env=dict(os.environ, USERPROFILE=HOME, HOME=HOME, PATH=path))
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

with tempfile.TemporaryDirectory() as tmp:  # AWS / Slack keys, a look-alike word, and a fake gitleaks
    d, git = repo(tmp)
    go = 'git add f.js && git commit -m x'
    for text, want in ((f'k = "{AWS}"', True), (f'k = "{SLACK}"', True), ('k = "ABCDEFGHIJKLMNOPQRST"', False)):
        (d / 'f.js').write_text(text + '\n')
        if blocks(go, d) != want:
            errors.append((f'f.js with {text[:9]}...', want))
    (d / 'f.js').write_text('console.log(3)\n')  # clean file: only a gitleaks finding can block
    if blocks(go, d):
        errors.append(('clean file, no gitleaks', False))
    if os.name != 'nt':  # a fake needs a shebang script; Windows would need a real .exe, so these rows skip there
        # the report goes to the file named by the last argument (--report-path <file>), as the real one writes it
        for name, body, want in (('finding', 'echo \'[{"File":"f.js","RuleID":"fake-rule"}]\' > "$out"; exit 1', True),
                                 ('error', 'echo \'[{"File":"f.js","RuleID":"fake-rule"}]\' > "$out"; exit 2', False),
                                 ('garbage', 'echo oops > "$out"; exit 1', False),
                                 ('hang', 'exec sleep 30', False)):
            bin = pathlib.Path(tmp).parent / f'fakebin-{name}'
            bin.mkdir(exist_ok=True)
            (bin / 'gitleaks').write_text('#!/bin/sh\nfor a; do out=$a; done\n' + body + '\n'); (bin / 'gitleaks').chmod(0o755)
            if blocks(go, d, str(bin) + os.pathsep + TOOLS) != want:
                errors.append((f'fake gitleaks: {name}', want))
            shutil.rmtree(bin)

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
