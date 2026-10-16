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
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home), BUILD_DIR=str(d / 'out'), ROOT_DIR=pathlib.Path(tmp).anchor)
    env.pop('UNSET_VAR_XYZ', None)
    (d / '.env').write_text('STRIPE_KEY=x\nexport DATABASE_URL=y\n')
    (d / 'tests' / 'cart.test.js').write_text("test('total', () => {\n  expect(total([1, 2])).toBe(3)\n  expect(total([])).toBe(0)\n})\n")

    def decision(tool, inp, node_args=()):
        r = subprocess.run(['node', *node_args, str(HOOK)], input=json.dumps({'tool_name': tool, 'tool_input': inp, 'cwd': str(d), 'session_id': 's'}),
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
        ('Bash', {'command': 'npm install -D typescript@5.4.5'}, 'allow'),  # pinned: a real package may have shipped a release today
        ('Bash', {'command': 'npm i reqeusts-helper-made-up-by-ai-xyz'}, 'deny'),
        ('Bash', {'command': 'pip install requests==2.32.0'}, 'allow'),
        ('Bash', {'command': 'pip install fastapi-auth-made-up-by-ai-xyz'}, 'deny'),
        ('Bash', {'command': 'pip install -r requirements.txt'}, 'allow'),
        # a temp folder made and removed in one command, a backup that keeps the .env name, a ref that is not Helena's
        ('Bash', {'command': 'tmp=$(mktemp -d) && cp -r src "$tmp" && rm -rf "$tmp"'}, 'allow'),
        ('Bash', {'command': 'for d in build dist; do rm -rf "$d"; done'}, 'allow'),
        ('Bash', {'command': 'cp .env .env.backup'}, 'allow'),
        ('Bash', {'command': 'git update-ref -d refs/heads/old-branch'}, 'allow'),
        ('Bash', {'command': 'npm install -D typescript@5.4.5 2>&1 > install.log'}, 'allow'),
        # 1. recursive delete of a variable (BUILD_DIR is set to a normal path below)
        ('Bash', {'command': 'rm -rf $HOME'}, 'ask'),
        ('Bash', {'command': 'rm -rf "$UNSET_VAR_XYZ"/*'}, 'ask'),
        ('Bash', {'command': 'rm -rf ${TMPDIR}/..'}, 'ask'),
        ('Bash', {'command': 'rm -rf "$BUILD_DIR"/*'}, 'ask'),
        ('Bash', {'command': 'rm -rf $ROOT_DIR'}, 'ask'),
        ('Bash', {'command': 'rm -rf %USERPROFILE%'}, 'ask'),
        ('Bash', {'command': 'Remove-Item -Recurse -Force $env:USERPROFILE'}, 'ask'),
        ('Bash', {'command': 'Remove-Item -Recurse -Force $env:UNSET_VAR_XYZ'}, 'ask'),
        ('Bash', {'command': 'rm -rf "$BUILD_DIR"/cache'}, 'allow'),
        ('Bash', {'command': 'rm -rf /tmp/sandbox-build'}, 'allow'),
        ('Bash', {'command': 'rm -rf node_modules'}, 'allow'),
        ('Bash', {'command': 'rm -f $UNSET_VAR_XYZ'}, 'allow'),
        # 2. delete through something else, decoded payload into a shell
        ('Bash', {'command': 'python -c "import shutil; shutil.rmtree(\'/\')"'}, 'ask'),
        ('Bash', {'command': 'python -c "import shutil; shutil.rmtree(\'build\')"'}, 'allow'),
        ('Bash', {'command': 'node -e "require(\'fs\').rmSync(\'/\',{recursive:true})"'}, 'ask'),
        ('Bash', {'command': 'node -e "require(\'fs\').rmSync(\'dist\',{recursive:true})"'}, 'allow'),
        ('Bash', {'command': 'npx rimraf ~'}, 'ask'),
        ('Bash', {'command': 'npx rimraf dist'}, 'allow'),
        ('Bash', {'command': 'find / -delete'}, 'ask'),
        ('Bash', {'command': 'find ~ -name "*.log" -delete'}, 'ask'),
        ('Bash', {'command': 'find . -name "*.pyc" -delete'}, 'allow'),
        ('Bash', {'command': 'echo cm0gLXJmIC8= | base64 -d | bash'}, 'ask'),
        ('Bash', {'command': 'echo cm0gLXJmIC8= | base64 --decode | sh'}, 'ask'),
        ('Bash', {'command': 'iex ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p)))'}, 'ask'),
        ('Bash', {'command': 'echo aGk= | base64 -d'}, 'allow'),
        # 3. the audit trail
        ('Bash', {'command': 'rm ~/.helena/audit.jsonl'}, 'ask'),
        ('Bash', {'command': 'rm -f $HOME/.helena/egress.jsonl'}, 'ask'),
        ('Bash', {'command': f'rm {home}/.helena/audit.jsonl'}, 'ask'),
        ('Bash', {'command': 'Remove-Item %USERPROFILE%\\.helena\\audit.jsonl'}, 'ask'),
        ('Bash', {'command': 'truncate -s 0 ~/.helena/audit.jsonl'}, 'ask'),
        ('Bash', {'command': '> ~/.helena/audit.jsonl'}, 'ask'),
        ('Bash', {'command': 'echo "" > "$HOME/.helena/audit.jsonl"'}, 'ask'),
        ('Bash', {'command': 'git update-ref -d refs/helena/turns'}, 'ask'),
        ('Bash', {'command': 'rm -rf .git/refs/helena'}, 'ask'),
        ('Bash', {'command': 'rm ~/.claude/projects/app/abc.jsonl'}, 'ask'),
        ('Bash', {'command': 'rm ~/.claude/projects/*/*.jsonl'}, 'ask'),
        ('Edit', {'file_path': str(home / '.helena' / 'audit.jsonl'), 'old_string': 'deny', 'new_string': 'allow'}, 'ask'),
        ('Write', {'file_path': str(home / '.helena' / 'audit.jsonl'), 'content': ''}, 'ask'),
        ('MultiEdit', {'file_path': str(home / '.helena' / 'egress.jsonl'), 'edits': []}, 'ask'),
        ('Bash', {'command': 'cat ~/.helena/audit.jsonl | tail -5'}, 'allow'),
        ('Bash', {'command': 'echo x >> ~/.helena/audit.jsonl'}, 'allow'),
        ('Bash', {'command': 'rm ~/.helena/tmp.txt'}, 'allow'),
        ('Bash', {'command': 'git update-ref refs/heads/x HEAD'}, 'allow'),
        ('Edit', {'file_path': str(d / 'audit.jsonl'), 'old_string': 'a', 'new_string': 'b'}, 'allow'),
        # 4. deleting a test
        ('Bash', {'command': 'rm tests/test_cart.py'}, 'ask'),
        ('Bash', {'command': 'git rm src/cart.test.js'}, 'ask'),
        ('Bash', {'command': 'Remove-Item spec/cart_spec.rb'}, 'ask'),
        ('Bash', {'command': 'del tests\\cart.test.js'}, 'ask'),
        ('Bash', {'command': 'rm notes.txt'}, 'allow'),
        ('Bash', {'command': 'rm -rf dist'}, 'allow'),
        ('Bash', {'command': 'rm -rf tests/__pycache__'}, 'allow'),
        # 5. .env through tricks
        ('Bash', {'command': "cat .e''nv"}, 'deny'),
        ('Bash', {'command': 'cat .e"n"v'}, 'deny'),
        ('Bash', {'command': 'cat .en?'}, 'deny'),
        ('Bash', {'command': 'cat ./.env*'}, 'deny'),
        ('Bash', {'command': 'python -c "print(open(\'.env\').read())"'}, 'deny'),
        ('Bash', {'command': 'node -e "console.log(require(\'fs\').readFileSync(\'.env\',\'utf8\'))"'}, 'deny'),
        ('Bash', {'command': 'cp .env /tmp/x && cat /tmp/x'}, 'deny'),
        ('Bash', {'command': 'mv .env /tmp/x'}, 'deny'),
        ('Bash', {'command': 'cat .env.example'}, 'allow'),
        ('Bash', {'command': 'cp .env.example .env'}, 'allow'),
        ('Bash', {'command': 'cat ".en?"'}, 'allow'),  # a quoted glob is not expanded by the shell
        ('Bash', {'command': 'cat *'}, 'allow'),  # * does not match dotfiles
        ('Bash', {'command': 'python -c "import os; print(os.environ.get(\'X\'), process.env)"'}, 'allow'),
    ]
    for tool, inp, want in cases:
        got, why = decision(tool, inp)
        if got != want:
            errors.append(f'{tool} {inp.get("command") or inp.get("file_path") or inp}: {got} (expected {want}) {why[:120]}')
    got, why = decision('Read', {'file_path': str(d / '.env')})
    if 'STRIPE_KEY, DATABASE_URL' not in why or '=x' in why:
        errors.append('the .env reason should list key names only: ' + why)

    # .helena/holdout: the human's hidden tests; same protection as .env, Write asks
    (d / '.helena' / 'holdout').mkdir(parents=True)
    (d / '.helena' / 'holdout' / 'test_a.py').write_text('def test_a():\n    assert 1 == 2, "SECRET-ASSERT"\n')
    H = str(d / '.helena' / 'holdout' / 'test_a.py')
    hold = [('Read', {'file_path': H}, 'deny'), ('Read', {'file_path': '.HELENA\\Holdout\\test_a.py'}, 'deny'),
            ('Read', {'file_path': '.helena/./holdout/../holdout/test_a.py'}, 'deny'),
            ('Grep', {'pattern': 'assert', 'path': '.helena/holdout'}, 'deny'), ('Grep', {'pattern': 'assert', 'path': '.helena'}, 'deny'),
            ('Glob', {'pattern': '.helena/holdout/*.py'}, 'deny'), ('Glob', {'pattern': '.helena/**'}, 'deny'),
            ('Bash', {'command': 'cat .helena/holdout/test_a.py'}, 'deny'), ('Bash', {'command': 'type .helena\\holdout\\test_a.py'}, 'deny'),
            ('Bash', {'command': 'Get-Content .helena/holdout/test_a.py'}, 'deny'), ('Bash', {'command': 'grep -r assert .helena/holdout'}, 'deny'),
            ('Bash', {'command': 'cat .helena/hold*/*'}, 'deny'), ('Bash', {'command': 'cat .helena/holdout/*.py'}, 'deny'),
            ('Bash', {'command': "cat .helena/hold''out/test_a.py"}, 'deny'),
            ('Bash', {'command': 'python -m pytest .helena/holdout -vv'}, 'deny'),
            ('Bash', {'command': 'git commit -m "document .helena/holdout"'}, 'allow'),
            ('Bash', {'command': "git commit -F - <<'EOF'\nnames .helena/holdout\nEOF\ncat .helena/holdout/test_a.py"}, 'deny'),
            ('Bash', {'command': 'python -c "print(open(\'.helena/holdout/test_a.py\').read())"'}, 'deny'),
            ('Bash', {'command': 'node -e "console.log(require(\'fs\').readFileSync(\'.helena\\\\holdout\\\\test_a.py\',\'utf8\'))"'}, 'deny'),
            ('Bash', {'command': 'cp .helena/holdout/test_a.py /tmp/x'}, 'deny'), ('Bash', {'command': 'cp .helena/holdout/test_a.py /tmp/'}, 'deny'),
            ('Bash', {'command': 'mv .helena/holdout /tmp/h'}, 'deny'),
            ('Write', {'file_path': H, 'content': 'x'}, 'ask'), ('Edit', {'file_path': H, 'old_string': 'a', 'new_string': 'b'}, 'ask'),
            ('Read', {'file_path': str(d / '.helena' / 'policy')}, 'allow'), ('Grep', {'pattern': 'x', 'path': 'src'}, 'allow'),
            ('Glob', {'pattern': '**/*.py'}, 'allow'), ('Bash', {'command': 'cat .helena/policy'}, 'allow'),
            ('Bash', {'command': 'cat *'}, 'allow'), ('Bash', {'command': 'cat holdout.txt'}, 'allow'), ('Write', {'file_path': str(d / 'src.js'), 'content': 'x'}, 'allow')]
    for tool, inp, want in hold:
        got, why = decision(tool, inp)
        if got != want or (want != 'allow' and ('hidden acceptance tests' not in why or 'SECRET' in why)):
            errors.append(f'holdout {tool} {inp.get("command") or inp.get("file_path") or inp}: {got} (expected {want}) {why[:120]}')

    (d / '.helena').mkdir(exist_ok=True)
    (d / '.helena' / 'policy').write_text('deny: terraform apply\nask: kubectl\nmcp: github, helena  # the only servers here\n')
    for tool, inp, want in [('Bash', {'command': 'terraform apply -auto-approve'}, 'deny'), ('Bash', {'command': 'kubectl get pods'}, 'ask'),
                            ('mcp__github__create_issue', {}, 'allow'), ('mcp__plugin_x_helena__helena_start', {}, 'allow'),
                            ('mcp__slack__post', {}, 'deny')]:
        got, why = decision(tool, inp)
        if got != want:
            errors.append(f'policy {tool} {inp}: {got} (expected {want})')

    # tests: spec-only (opt-in): a NEW test file asks, an edit of an existing one or a non-test file does not
    spec = [('Write', {'file_path': str(d / 'tests' / 'test_new.py'), 'content': 'x'}), ('Write', {'file_path': str(d / 'cart_test.go'), 'content': 'x'}),
            ('Write', {'file_path': str(d / 'a.spec.tsx'), 'content': 'x'}), ('Write', {'file_path': test, 'content': 'expect(1).toBe(1)\nexpect(2).toBe(2)'}),
            ('Edit', {'file_path': test, 'old_string': 'toBe(3)', 'new_string': 'toBe(3)'}), ('Write', {'file_path': str(d / 'src.js'), 'content': 'x'})]
    for tool, inp in spec:
        got, why = decision(tool, inp)
        if got != 'allow':
            errors.append(f'spec-only off: {inp["file_path"]} {got}')
    (d / '.helena' / 'delegate').write_text('model: sonnet\ntests: spec-only\n')
    for (tool, inp), want in zip(spec, ['ask', 'ask', 'ask', 'allow', 'allow', 'allow']):
        got, why = decision(tool, inp)
        if got != want or (want == 'ask' and 'spec-only' not in why):
            errors.append(f'spec-only on: {tool} {inp["file_path"]}: {got} (expected {want})')
    (d / '.helena' / 'delegate').unlink()

    log = home / '.helena' / 'audit.jsonl'
    rows = [json.loads(l) for l in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
    if not any(r['decision'] == 'deny' and r['hook'] == 'gate' for r in rows) or any('=x' in r['why'] for r in rows):
        errors.append('audit log missing or leaking values')

    # a command that goes out leaves its hosts in the egress log, without the credentials in the URL
    decision('Bash', {'command': 'curl -s https://bob:hunter2@api.example.com/v1/users | head -5 && wget http://files.example.org/a.zip'})
    decision('Bash', {'command': 'echo see https://docs.example.com/guide'})
    out = home / '.helena' / 'egress.jsonl'
    went = [json.loads(l)['to'] for l in out.read_text(encoding='utf-8').splitlines()] if out.exists() else []
    if went != ['api.example.com', 'files.example.org']:
        errors.append(f'egress log: {went}')

    # 6. a release under 72 h old with no version named asks and names the previous one; fetch is faked, so no real package matters
    mock = pathlib.Path(tmp) / 'mock.js'
    mock.write_text("""const h = 36e5, iso = ago => new Date(Date.now() - ago).toISOString(), J = o => ({ ok: true, status: 200, json: async () => o });
global.fetch = async u => { u = String(u);
  if (u.includes('api.npmjs.org')) return J({ downloads: 1e6 });
  if (u.includes('/-/v1/search')) { const n = decodeURIComponent(u.match(/text=([^&]+)/)[1]);
    return J({ objects: [{ package: { name: n === 'lookalike' ? 'other' : n, version: '2.0.0', date: iso(n.includes('fresh') ? 5 * h : 900 * h) } }] }); }
  if (u.startsWith('https://registry.npmjs.org/')) return J({ 'dist-tags': { latest: '2.0.0' }, versions: { '1.9.0': {}, '1.10.0': {}, '2.0.0': {}, '2.1.0-beta.1': {} } });
  const n = u.split('/pypi/')[1].split('/')[0], rel = (ago) => [{ upload_time_iso_8601: iso(ago) }];
  return J({ info: { version: '2.0' }, releases: { '0.9': rel(900 * 24 * h), '1.0': rel(400 * 24 * h), '2.0': rel(n.includes('fresh') ? 5 * h : 400 * 24 * h) } }); };
""", encoding='utf-8')
    for cmd, want, hint in [('npm install freshpkg', 'ask', 'freshpkg@1.10.0'), ('npm i @scope/freshpkg', 'ask', '@1.10.0'), ('pip install freshpy', 'ask', 'freshpy==1.0'),
                            ('npm install freshpkg@2.0.0', 'allow', ''), ('npm install freshpkg@latest', 'ask', '1.10.0'), ('pip install freshpy==2.0', 'allow', ''),
                            ('npm install oldpkg', 'allow', ''), ('pip install oldpy', 'allow', ''), ('npm install lookalike', 'allow', '')]:
        got, why = decision('Bash', {'command': cmd}, ('-r', str(mock)))
        if got != want or hint not in why:
            errors.append(f'fresh release {cmd}: {got} (expected {want}) {why[:160]}')

for e in errors:
    print('failed:', e)
print('ok: secrets, packages, destructive commands, tests, policy and audit' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
