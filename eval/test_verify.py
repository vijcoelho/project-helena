"""Memory that checks itself, the verified handoff, one instruction file for every AI, and agent messages that are not
requests. No LLM: python eval/test_verify.py
"""
import json, os, pathlib, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / 'helena' / 'hooks'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)


def node(script, cwd, env, ev=None):
    return subprocess.run(['node', str(HOOKS / script)], input=json.dumps(ev) if ev is not None else '', cwd=cwd,
                          capture_output=True, text=True, encoding='utf-8', env=env, timeout=30).stdout


with tempfile.TemporaryDirectory() as tmp:
    t = pathlib.Path(tmp)
    home, vault, repo = t / 'home', t / 'vault', t / 'shop'
    (home / '.helena').mkdir(parents=True)
    (vault / 'Memory').mkdir(parents=True)
    (repo / 'src').mkdir(parents=True)
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home), HELENA_VAULT=str(vault), HELENA_EVAL='1')
    git = lambda *a: subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *a], cwd=repo, check=True, capture_output=True)
    (repo / 'src' / 'db.js').write_text('export function connectPostgres() {}\n')
    git('init', '-q'); git('add', '.'); git('commit', '-qm', 'init')

    mem = vault / 'Memory'
    (mem / 'cache-redis.md').write_text('---\ntype: fact\ndescription: cache uses redis\nproject: shop\n'
                                        'checks: src/cache/redis.js\n---\nThe cache is Redis, in src/cache/redis.js.\n')
    (mem / 'db-postgres.md').write_text('---\ntype: fact\ndescription: database is postgres\nproject: shop\n'
                                        'checks: src/db.js#connectPostgres\n---\nPostgres, connectPostgres in src/db.js.\n')
    (mem / 'old-deadline.md').write_text('---\ntype: fact\ndescription: launch deadline friday\nproject: shop\nuntil: 2020-01-01\n---\nx\n')
    (mem / 'other-project.md').write_text('---\ntype: fact\ndescription: belongs elsewhere\nproject: blog\n---\nx\n')
    (repo / '.helena' / 'memory').mkdir(parents=True)
    (repo / '.helena' / 'memory' / 'team-deploy.md').write_text('---\ntype: rule\ndescription: deploy only through the pipeline\n---\nNever deploy by hand.\n')

    # 1. memory index: a failing check or an expired date is marked STALE, a passing one is not, the team note shows up
    out = node('start.js', repo, env, {'transcript_path': str(t / '.claude' / 'projects' / 'x' / 's.jsonl')})
    line = lambda slug: next((l for l in out.splitlines() if l.startswith(f'- {slug}:')), '')
    check('STALE: src/cache/redis.js no longer exists' in line('cache-redis'), 'missing file not flagged: ' + line('cache-redis'))
    check('STALE' not in line('db-postgres') and line('db-postgres'), 'passing check flagged or note missing')
    check('expired on 2020-01-01' in line('old-deadline'), 'expired note not flagged')
    check(not line('other-project'), 'another project\'s note leaked in')
    check('(team)' in line('team-deploy'), 'team note missing')

    # the same mark when router.js hands a matching note over
    (repo / 'src' / 'db.js').write_text('export function connectMysql() {}\n')
    out = node('router.js', repo, env, {'prompt': 'which database does the shop use, postgres?', 'session_id': 'r1', 'cwd': str(repo)})
    check('db-postgres.md' in out and 'connectPostgres is no longer in src/db.js' in out, 'router did not mark the stale note:\n' + out)

    # 2. supersedes: the replaced note goes to Archive with a pointer to the new one
    r = subprocess.run([sys.executable, str(ROOT / 'helena' / 'distill.py'), '--remember', 'test'], env=env, capture_output=True,
                       text=True, input=json.dumps({'memories': [{'slug': 'cache-postgres', 'description': 'cache moved to postgres',
                       'body': 'The cache is now a Postgres table.', 'project': 'shop', 'checks': 'src/db.js',
                       'supersedes': ['cache-redis']}]}))
    archived = vault / 'Archive' / 'cache-redis.md'
    check(r.returncode == 0 and not (mem / 'cache-redis.md').exists() and archived.exists(), 'superseded note not archived: ' + r.stderr)
    check(archived.exists() and 'Superseded by [[cache-postgres]]' in archived.read_text(), 'no pointer to the new note')
    check('checks: src/db.js' in (mem / 'cache-postgres.md').read_text(), 'checks not written in the new note')

    # 3. handoff checked against the repo: files it names that are gone, files changed after it
    (repo / 'HANDOFF.md').write_text('# Handoff\n## Next\n- finish `src/cart/total.js` and src/db.js\n')
    old = time.time() - 600
    os.utime(repo / 'HANDOFF.md', (old, old))
    out = node('start.js', repo, env, {'transcript_path': str(t / '.claude' / 'projects' / 'x' / 's.jsonl')})
    check('names files that no longer exist: src/cart/total.js' in out, 'missing file in handoff not reported:\n' + out)
    check('changed after it was written: ' in out and 'src/db.js' in out.split('changed after it was written: ')[1][:200], 'later change not reported')
    check('restate in one line the next step' in out, 'no restate request')

    # 4. one instruction file: Claude gets AGENTS.md when the repo has no CLAUDE.md; Codex reads AGENTS.md itself
    (repo / 'AGENTS.md').write_text('Run tests with npm test. Use pnpm.\n')
    claude = node('start.js', repo, env, {'transcript_path': str(t / '.claude' / 'projects' / 'x' / 's.jsonl')})
    codex = node('start.js', repo, env, {'transcript_path': str(t / '.codex' / 'sessions' / 'r.jsonl')})
    check('Use pnpm.' in claude, 'Claude did not get AGENTS.md')
    check('Use pnpm.' not in codex, 'Codex got AGENTS.md twice')

    # 5. a subagent's report is not a request: no kit, no plugin turned back on
    (home / '.helena' / 'kits.json').write_text(json.dumps({'pagamento': {'keywords': ['stripe', 'pix'], 'note': 'KIT-FIRED'}}))
    agent = 'Another Claude session sent a message:\n<agent-message from="x">pricing with stripe and pix</agent-message>'
    check('KIT-FIRED' not in node('router.js', repo, env, {'prompt': agent, 'session_id': 'r2', 'cwd': str(repo)}), 'kit fired on agent text')
    check('KIT-FIRED' in node('router.js', repo, env, {'prompt': 'add stripe and pix checkout', 'session_id': 'r3', 'cwd': str(repo)}),
          'kit no longer fires on a real request')

for e in errors:
    print('failed:', e)
print('ok: stale notes flagged, supersedes archives, handoff checked, AGENTS.md shared, agent text ignored' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
