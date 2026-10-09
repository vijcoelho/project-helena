"""The gate hook: .env stays out of the context, made-up packages are denied, destructive commands and weakened tests ask
first, the team policy applies, and every decision is logged. No LLM; the package checks need the internet.

    python eval/test_gate.py
"""
import json, os, pathlib, subprocess, sys, tempfile

HOOK = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks' / 'gate.js'
errors = []

with tempfile.TemporaryDirectory() as tmp:
    d, home = pathlib.Path(tmp) / 'app', pathlib.Path(tmp) / 'home'
    (d / 'tests').mkdir(parents=True)
    home.mkdir()
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home))
    (d / '.env').write_text('STRIPE_KEY=x\nexport DATABASE_URL=y\n')
    (d / 'tests' / 'cart.test.js').write_text("test('total', () => {\n  expect(total([1, 2])).toBe(3)\n  expect(total([])).toBe(0)\n})\n")

    def decision(tool, inp):
        r = subprocess.run(['node', str(HOOK)], input=json.dumps({'tool_name': tool, 'tool_input': inp, 'cwd': str(d), 'session_id': 's'}),
                           capture_output=True, text=True, encoding='utf-8', env=env, timeout=30)
        out = json.loads(r.stdout)['hookSpecificOutput'] if r.stdout.strip() else {}
        return out.get('permissionDecision', 'allow'), out.get('permissionDecisionReason', '')

    test = str(d / 'tests' / 'cart.test.js')
    cases = [
        ('Read', {'file_path': str(d / '.env')}, 'deny'),
        ('Read', {'file_path': str(d / '.env.example')}, 'allow'),
        ('Read', {'file_path': str(d / 'index.js')}, 'allow'),
        ('Bash', {'command': 'cat .env'}, 'deny'),
        ('Bash', {'command': 'grep STRIPE apps/web/.env.local'}, 'deny'),
        ('Bash', {'command': 'cat .env.example && source .env'}, 'allow'),
        ('Grep', {'pattern': 'KEY', 'path': '.env'}, 'deny'),
        ('Edit', {'file_path': test, 'old_string': '  expect(total([])).toBe(0)\n', 'new_string': ''}, 'ask'),
        ('Edit', {'file_path': test, 'old_string': "test('total'", 'new_string': "test.skip('total'"}, 'ask'),
        ('Edit', {'file_path': test, 'old_string': '})\n', 'new_string': '  expect(total([5])).toBe(5)\n})\n'}, 'allow'),
        ('Write', {'file_path': str(d / 'tests' / 'new.test.js'), 'content': "test('x', () => {})\n"}, 'allow'),
        ('Edit', {'file_path': str(d / 'src.js'), 'old_string': 'assert(x)', 'new_string': ''}, 'allow'),
        ('Bash', {'command': 'psql -c "DROP TABLE users"'}, 'ask'),
        ('Bash', {'command': 'psql -c "DELETE FROM users WHERE id = 1"'}, 'allow'),
        ('Bash', {'command': 'git push --force origin main'}, 'ask'),
        ('Bash', {'command': 'git push --force-with-lease'}, 'allow'),
        ('Bash', {'command': 'rm -rf ./build dist'}, 'allow'),
        ('Bash', {'command': 'rm -rf /'}, 'ask'),
        ('Bash', {'command': 'git reset --hard HEAD~1'}, 'ask'),
        ('Bash', {'command': 'npm install -D typescript'}, 'allow'),
        ('Bash', {'command': 'npm i reqeusts-helper-made-up-by-ai-xyz'}, 'deny'),
        ('Bash', {'command': 'pip install requests==2.32.0'}, 'allow'),
        ('Bash', {'command': 'pip install fastapi-auth-made-up-by-ai-xyz'}, 'deny'),
        ('Bash', {'command': 'pip install -r requirements.txt'}, 'allow'),
    ]
    for tool, inp, want in cases:
        got, why = decision(tool, inp)
        if got != want:
            errors.append(f'{tool} {inp.get("command") or inp.get("file_path") or inp}: {got} (expected {want}) {why[:120]}')
    got, why = decision('Read', {'file_path': str(d / '.env')})
    if 'STRIPE_KEY, DATABASE_URL' not in why or '=x' in why:
        errors.append('the .env reason should list key names only: ' + why)

    (d / '.helena').mkdir()
    (d / '.helena' / 'policy').write_text('deny: terraform apply\nask: kubectl\nmcp: github, helena  # the only servers here\n')
    for tool, inp, want in [('Bash', {'command': 'terraform apply -auto-approve'}, 'deny'), ('Bash', {'command': 'kubectl get pods'}, 'ask'),
                            ('mcp__github__create_issue', {}, 'allow'), ('mcp__plugin_x_helena__helena_start', {}, 'allow'),
                            ('mcp__slack__post', {}, 'deny')]:
        got, why = decision(tool, inp)
        if got != want:
            errors.append(f'policy {tool} {inp}: {got} (expected {want})')

    log = home / '.helena' / 'audit.jsonl'
    rows = [json.loads(l) for l in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
    if not any(r['decision'] == 'deny' and r['hook'] == 'gate' for r in rows) or any('=x' in r['why'] for r in rows):
        errors.append('audit log missing or leaking values')

for e in errors:
    print('failed:', e)
print('ok: secrets, packages, destructive commands, tests, policy and audit' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
