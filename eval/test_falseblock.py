"""False-block guard: ordinary calls of a normal coding session must pass gate.js untouched (no deny, no ask),
also with `tests: spec-only` on.

    python eval/test_falseblock.py
"""
import json, os, pathlib, subprocess, sys, tempfile

HOOK = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks' / 'gate.js'

with tempfile.TemporaryDirectory() as tmp:
    d, home = pathlib.Path(tmp) / 'app', pathlib.Path(tmp) / 'home'
    (d / 'src').mkdir(parents=True)
    (d / 'tests').mkdir()
    home.mkdir()
    subprocess.run(['git', 'init', '-q'], cwd=d, check=True)
    (d / 'src' / 'cart.js').write_text('exports.total = a => a.reduce((x, y) => x + y, 0)\n')
    (d / 'requirements.txt').write_text('requests==2.32.0\n')
    (d / 'tests' / 'cart.test.js').write_text("test('total', () => {\n  expect(total([1, 2])).toBe(3)\n})\n")
    env = {k: v for k, v in os.environ.items() if k != 'HELENA_DISTILLING'}
    env.update(HOME=str(home), USERPROFILE=str(home), HELENA_VAULT=str(home / 'Helena'))
    s = lambda *p: str(d.joinpath(*p))
    test = s('tests', 'cart.test.js')
    calls = [
        ('Read', {'file_path': s('src', 'cart.js')}), ('Read', {'file_path': s('package.json')}), ('Read', {'file_path': test}),
        ('Grep', {'pattern': 'total', 'path': s('src')}), ('Grep', {'pattern': 'TODO', 'glob': '*.js'}),
        ('Glob', {'pattern': 'src/**/*.js'}), ('Glob', {'pattern': '**/*.test.js', 'path': str(d)}),
        ('Bash', {'command': 'npm test'}), ('Bash', {'command': 'pytest -q'}), ('Bash', {'command': 'pytest -q tests/test_cart.py -x'}),
        ('Bash', {'command': 'git status'}), ('Bash', {'command': 'git diff'}), ('Bash', {'command': 'git log --oneline -5'}),
        ('Bash', {'command': 'git add src/cart.js'}), ('Bash', {'command': 'git commit -m "fix total"'}),
        ('Bash', {'command': 'ls -la src'}), ('Bash', {'command': 'node script.js'}), ('Bash', {'command': 'python -m pytest'}),
        ('Bash', {'command': 'pip install -r requirements.txt'}), ('Bash', {'command': 'cat src/cart.js | head -20'}),
        ('Bash', {'command': 'grep -rn total src'}), ('Bash', {'command': 'rm -rf node_modules dist'}),
        ('Bash', {'command': 'cat .env.example'}), ('Bash', {'command': 'npx tsc --noEmit && npm run build'}),
        ('Write', {'file_path': s('src', 'format.js'), 'content': 'exports.fmt = n => n.toFixed(2)\n'}),
        ('Write', {'file_path': s('README.md'), 'content': '# app\n'}),
        ('Edit', {'file_path': s('src', 'cart.js'), 'old_string': 'x + y', 'new_string': 'x + y * 1'}),
        ('Edit', {'file_path': test, 'old_string': '})\n', 'new_string': '  expect(total([5])).toBe(5)\n})\n'}),
        ('Edit', {'file_path': test, 'old_string': "test('total'", 'new_string': "test('total of two'"}),
    ]

    def decision(tool, inp):
        r = subprocess.run(['node', str(HOOK)], input=json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': inp,
                           'cwd': str(d), 'session_id': 's'}), capture_output=True, text=True, encoding='utf-8', env=env, timeout=30)
        o = json.loads(r.stdout)['hookSpecificOutput'] if r.stdout.strip() else {}
        return o.get('permissionDecision', 'allow'), o.get('permissionDecisionReason', '')

    bad = []
    for spec in (False, True):
        (d / '.helena').mkdir(exist_ok=True)
        (d / '.helena' / 'delegate').write_text('tests: spec-only\n' if spec else 'tests: off\n')
        for tool, inp in calls:
            dec, why = decision(tool, inp)
            if dec != 'allow':
                bad.append(f"{tool} {inp.get('command') or inp.get('file_path') or inp.get('pattern')} [spec-only={'on' if spec else 'off'}]: {dec} {why[:80]}")

if bad:
    print('FALSE BLOCKS:\n  ' + '\n  '.join(bad))
    sys.exit(1)
print(f'ok: {len(calls)} clean calls allowed (spec-only on and off)')
