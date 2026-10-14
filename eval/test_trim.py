"""Tests the helena/hooks/trim.js hook, without calling Claude: a command that floods the context is refused, and one
that only needs a quieter flag gets the flag and runs.

    python eval/test_trim.py
"""
import json, os, pathlib, stat, subprocess, sys, tempfile

HOOK = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks' / 'trim.js'
DENY, ALLOW = 'deny', ''


def got(tool, inp, folder, env=None):
    """'deny', the command it was rewritten to, or '' when the hook says nothing."""
    r = subprocess.run(['node', str(HOOK)], input=json.dumps({'tool_name': tool, 'tool_input': inp, 'cwd': str(folder)}),
                       capture_output=True, text=True, env=env)
    out = json.loads(r.stdout)['hookSpecificOutput'] if r.stdout.strip() else {}
    return out.get('permissionDecision') or (out.get('updatedInput') or {}).get('command', ''), out.get('additionalContext', '')


with tempfile.TemporaryDirectory() as tmp:
    d = pathlib.Path(tmp)
    (d / 'node_modules').mkdir()
    (d / 'big.log').write_text('x' * 200_000)
    (d / 'small.js').write_text('console.log(1)\n')
    (d / 'package-lock.json').write_text('{}')
    cases = [
        # ---- refused: no flag makes these lean without changing what they mean
        ('Bash', {'command': 'cat big.log'}, DENY),
        ('Bash', {'command': 'cat big.log | tail -50'}, ALLOW),
        ('Bash', {'command': 'cat big.log  # helena:full'}, ALLOW),
        ('Bash', {'command': 'cat small.js'}, ALLOW),
        ('Bash', {'command': 'cat package-lock.json'}, DENY),
        ('Bash', {'command': 'git log -p'}, DENY),
        ('Bash', {'command': 'git log --stat'}, DENY),
        ('Bash', {'command': 'ls -R'}, DENY),
        ('PowerShell', {'command': 'Get-Content big.log'}, DENY),
        ('Read', {'file_path': str(d / 'big.log')}, DENY),
        ('Read', {'file_path': str(d / 'big.log'), 'limit': 100}, ALLOW),
        ('Read', {'file_path': str(d / 'package-lock.json')}, DENY),
        ('Read', {'file_path': str(d / 'dist' / 'app.min.js')}, DENY),
        ('Read', {'file_path': str(d / 'small.js')}, ALLOW),
        # ---- rewritten: the quiet flag goes in, no refusal and no second model call
        ('Bash', {'command': 'git log'}, 'git log --oneline -n 20'),
        ('Bash', {'command': 'git log --pretty=format:%s -- src'}, 'git log -n 20 --pretty=format:%s -- src'),
        ('Bash', {'command': 'cd app && git log'}, 'cd app && git log --oneline -n 20'),
        ('Bash', {'command': 'git log --oneline -20'}, ALLOW),
        ('Bash', {'command': 'git log -p -3'}, ALLOW),
        ('Bash', {'command': 'git log | grep fix'}, ALLOW),
        ('Bash', {'command': 'git status'}, 'git status -sb'),
        ('PowerShell', {'command': 'git status; git log'}, 'git status -sb; git log --oneline -n 20'),
        ('Bash', {'command': 'git status --porcelain'}, ALLOW),
        ('Bash', {'command': 'grep -rn foo .'}, 'grep --exclude-dir=node_modules --exclude-dir=.git -rn foo .'),
        ('Bash', {'command': 'grep -rn foo . | head'}, 'grep --exclude-dir=node_modules --exclude-dir=.git -rn foo . | head'),
        ('Bash', {'command': 'grep -rn foo src --include=*.js'}, ALLOW),
        ('Bash', {'command': 'grep -n foo small.js'}, ALLOW),
        ('Bash', {'command': 'python -m pytest tests -x'}, 'python -m pytest -q --tb=short tests -x'),
        ('Bash', {'command': 'pytest -v'}, 'pytest --tb=short -v'),
        ('Bash', {'command': 'pytest -q --tb=long'}, ALLOW),
        ('Bash', {'command': 'pytest | tee out.txt'}, ALLOW),
        ('Bash', {'command': 'pytest > out.txt'}, ALLOW),
        ('Bash', {'command': 'pip install -r requirements.txt'}, 'pip install -q -r requirements.txt'),
        ('Bash', {'command': 'npm install express'}, 'npm install --no-fund --loglevel=error express'),
        ('Bash', {'command': 'npm test'}, ALLOW),
        ('Bash', {'command': 'cargo test'}, 'cargo test -q'),
        # ---- never inside a quoted string, a heredoc, or when the escape hatch is there
        ('Bash', {'command': 'git commit -m "docs; git status"'}, ALLOW),
        ('Bash', {'command': "git commit -m 'fix && pytest tests'"}, ALLOW),
        ('Bash', {'command': 'cat <<EOF > notes.txt\ngit status\nEOF'}, ALLOW),
        ('Bash', {'command': 'git log  # helena:full'}, ALLOW),
    ]
    errors = [f'{t} {i}: got {got(t, i, d)[0]!r}, expected {want!r}' for t, i, want in cases if got(t, i, d)[0] != want]

    # what was cut is said to the AI; a flag that cuts nothing says nothing (it would be paid on every message)
    if 'last 20 commits' not in got('Bash', {'command': 'git log'}, d)[1]:
        errors.append('git log: the AI is not told the history was cut')
    if got('Bash', {'command': 'git status'}, d)[1]:
        errors.append('git status: a note for a flag that cuts nothing')

    # rtk on PATH goes first; an answer that does not name rtk is never run. A fake rtk needs a real executable, so the
    # check runs where a script with a shebang is one (not on Windows).
    if os.name != 'nt':
        fake = d / 'bin' / 'rtk'
        fake.parent.mkdir()
        fake.write_text('#!/bin/sh\ncase "$2" in "git diff") echo "rtk git diff";; "ls") echo "rm -rf /";; *) exit 1;; esac\n')
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        env = dict(os.environ, PATH=str(fake.parent) + os.pathsep + os.environ['PATH'])
        for cmd, want in [('git diff', 'rtk git diff'), ('ls', ALLOW), ('git status', 'git status -sb')]:
            if got('Bash', {'command': cmd}, d, env)[0] != want:
                errors.append(f'rtk: {cmd!r} gave {got("Bash", {"command": cmd}, d, env)[0]!r}, expected {want!r}')

for e in errors:
    print('failed:', e)
print('ok' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
