"""The Helena app's server, no LLM, no browser: python eval/test_app.py

In a fake home with one Claude session, a done check that passed, a blocked command, a router hand-over (made by the
real router.js), an expired memory note and Helena's own cost, /api/state shows each of them where the window expects
it. Only 127.0.0.1 with its own Host header is answered, only GET, and a second launch reuses the running server.
"""
import json, os, pathlib, subprocess, tempfile, time, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVER = ROOT / 'helena' / 'app' / 'server.js'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)
        print('failed:', what)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:  # the server asks agy for its models; agy may still hold a log in this fake HOME
    h = pathlib.Path(tmp)
    helena, memory, proj = h / '.helena', h / 'vault' / 'Memory', h / '.claude' / 'projects' / 'C--work-shop'
    for d in (helena, memory, proj):
        d.mkdir(parents=True)
    env = dict(os.environ, USERPROFILE=tmp, HOME=tmp, HELENA_VAULT=str(h / 'vault'))
    cwd = str(pathlib.Path('/work/shop').resolve())  # not under the temp folder: eval sandboxes there are hidden
    now = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())
    (proj / 's1.jsonl').write_text('\n'.join(json.dumps(l) for l in [
        {'type': 'user', 'cwd': cwd, 'message': {'content': [{'type': 'text', 'text': '<system-reminder>x</system-reminder>'},
                                                             {'type': 'text', 'text': 'fix <b>the</b> cart total'}]}},
        {'type': 'assistant', 'cwd': cwd, 'timestamp': now + 'Z', 'message': {'model': 'claude-opus-5-5', 'content': [],
         'usage': {'input_tokens': 10, 'cache_read_input_tokens': 41990, 'cache_creation': {'ephemeral_1h_input_tokens': 5}}}},
    ]) + '\n')
    (helena / 'audit.jsonl').write_text(json.dumps({'ts': '2026-01-01T10:00:00', 'project': 'shop', 'session': 's1', 'hook': 'gate',
                                                    'tool': 'Bash', 'decision': 'deny', 'what': 'rm -rf /', 'why': 'destructive'}) + '\n')
    (helena / 'events.jsonl').write_text(json.dumps({'ts': now, 'project': 'shop', 'session': 's1', 'kind': 'done',
                                                     'cmd': 'npm test --silent', 'holdout': True, 'edited': ['cart.js']}) + '\n')
    (helena / 'ledger.jsonl').write_text(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'what': 'distill', 'cost': 0.25}) + '\n')
    (helena / 'limits-claude.json').write_text(json.dumps({'five_hour': {'used_percentage': 30, 'resets_at': int(time.time()) + 3600}}))
    (memory / 'cart-total-cents.md').write_text('---\ntype: fact\ndescription: cart total is kept in cents\n---\nCart total in cents.\n')
    (memory / 'old-deploy.md').write_text('---\ntype: fact\ndescription: deploy on Friday\nuntil: 2020-01-01\n---\nDeploy on Friday.\n')

    # the real router hands over the matching note and logs it for the app
    subprocess.run(['node', str(ROOT / 'helena' / 'hooks' / 'router.js')], input=json.dumps(
        {'prompt': 'fix the cart total cents', 'session_id': 's1', 'cwd': cwd}), capture_output=True, text=True, env=env, timeout=30)

    srv = subprocess.Popen(['node', str(SERVER), '--serve', '--port', '0', '--no-open'], stdout=subprocess.PIPE, text=True, env=env)
    try:
        url = srv.stdout.readline().strip()
        port = url.split(':')[2].strip('/')

        def get(path, host=None, method='GET'):
            req = urllib.request.Request(url.rstrip('/') + path, method=method, headers={'Host': host} if host else {})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, r.read().decode('utf-8')
            except urllib.error.HTTPError as e:
                return e.code, ''

        code, page = get('/')
        check(code == 200 and '<title>Helena</title>' in page, f'page not served: {code}')
        check(get('/api/state', host='evil.example')[0] == 403, 'answered a foreign Host header')
        check(get('/api/state', method='POST')[0] == 405, 'answered a POST')
        check(get('/nope')[0] == 404, 'unknown path not 404')
        s = json.loads(get('/api/state')[1])

        se = s['sessions'][0] if s['sessions'] else {}
        check(se.get('project') == 'shop' and se.get('ctx') == 42000 and se.get('model') == 'claude-opus-5-5', 'session: ' + str(se))
        check(se.get('asked') == 'fix <b>the</b> cart total', 'last request should skip the system reminder: ' + str(se.get('asked')))
        check((se.get('check') or {}).get('ok') is True and se['check']['cmd'] == 'npm test --silent', 'done check not on the session: ' + str(se.get('check')))
        kinds = [e['kind'] for e in s['feed']]
        check(kinds[:1] in (['done'], ['router']) and 'deny' in kinds, 'feed order or content: ' + str(kinds))
        router = next((e for e in s['feed'] if e['kind'] == 'router'), {})
        check(router.get('notes') == ['cart-total-cents.md'], 'router hand-over not logged: ' + str(router))
        check(s['memory']['total'] == 2 and [n['file'] for n in s['memory']['stale']] == ['old-deploy'] and 'expired' in s['memory']['stale'][0]['stale'],
              'memory: ' + str(s['memory']))
        check(abs(s['cost']['today'] - 0.25) < 1e-9, 'cost: ' + str(s['cost']))
        claude = next((a for a in s['limits'] if a['name'] == 'Claude'), None)
        check(claude is None or claude.get('pct') == 30, 'limits: ' + str(claude))  # None when no claude CLI on PATH

        again = subprocess.run(['node', str(SERVER), '--no-open'], capture_output=True, text=True, env=env, timeout=10).stdout
        check(f'already running: http://127.0.0.1:{port}/' in again, 'second launch did not reuse the server: ' + again)
    finally:
        srv.kill()

# the server runs detached, with no console: on Windows any program it starts without windowsHide flashes a terminal
import re
for f in ('server.js', 'shell.js'):
    src = (SERVER.parent / f).read_text(encoding='utf8')
    for m in re.finditer(r'(?<![.\w])(spawn|spawnSync|execFile|execFileSync|execSync|exec)\(|\)\.(spawn|execFile|execFileSync)\(', src):
        i, depth = m.end(), 1  # the whole call, up to its closing parenthesis
        while depth:
            depth += {'(': 1, ')': -1}.get(src[i], 0)
            i += 1
        call = src[m.start():i]
        check('windowsHide: true' in call, f'{f}: starts a program without windowsHide: {call.strip()[:90]}')

print(f'{len(errors)} error(s)' if errors else 'ok: sessions, done checks, blocks, hand-overs, stale notes, cost and limits reach the app; foreign hosts refused')
raise SystemExit(1 if errors else 0)
