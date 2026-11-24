"""Tests Phase 3 memory routing: path-scoped delivery on Read/Edit (checks: & paths:), BM25 + PT/EN stemming, and
1-hop [[wikilinks]]. No LLM.

    python eval/test_memory_routing.py
"""
import json, os, pathlib, subprocess, sys, tempfile

HOOKS = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)


with tempfile.TemporaryDirectory() as tmp:
    t = pathlib.Path(tmp)
    home, vault, repo = t / 'home', t / 'vault', t / 'shop'
    (home / '.helena').mkdir(parents=True)
    mem = vault / 'Memory'
    mem.mkdir(parents=True)
    (repo / 'src' / 'auth').mkdir(parents=True)
    (repo / 'src' / 'ui').mkdir(parents=True)
    (repo / 'src' / 'auth' / 'jwt.ts').write_text('export function verifyToken() {}\n', encoding='utf-8')
    (repo / 'src' / 'ui' / 'modal.css').write_text('.modal {}\n', encoding='utf-8')
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home), HELENA_VAULT=str(vault), HELENA_EVAL='1')

    # Note 1: bound via checks: to src/auth/jwt.ts
    (mem / 'auth-samesite.md').write_text(
        '---\ntype: rule\ndescription: cookie de sessao exige SameSite Lax\nproject: shop\n'
        'checks: src/auth/jwt.ts#verifyToken\n---\nAlways set SameSite=Lax on auth cookies.\n', encoding='utf-8'
    )
    # Note 2: bound via paths: glob to src/ui/*.css
    (mem / 'ui-zindex.md').write_text(
        '---\ntype: rule\ndescription: modais precisam ficar acima do header fixo\nproject: shop\n'
        'paths: src/ui/*.css\n---\nKeep modal z-index >= 50 so it never hides under the sticky bar.\n', encoding='utf-8'
    )
    # Note 3 & 4: PT/EN inflections + 1-hop [[wikilink]]
    (mem / 'db-migracao.md').write_text(
        '---\ntype: rule\ndescription: autenticacao e migracao do banco de dados rodam via prisma\nproject: shop\n---\n'
        'Run prisma migrate deploy on staging first. Related: [[staging-ssh]].\n', encoding='utf-8'
    )
    (mem / 'staging-ssh.md').write_text(
        '---\ntype: fact\ndescription: acesso ao servidor de homologacao\nproject: shop\n---\n'
        'Staging lives at deploy@staging.internal port 2222.\n', encoding='utf-8'
    )

    def run_hook(script, ev):
        r = subprocess.run(['node', str(HOOKS / script)], input=json.dumps({'cwd': str(repo), **ev}),
                           cwd=repo, capture_output=True, text=True, encoding='utf-8', env=env, timeout=30)
        return r.stdout

    # 1. Path-scoped via checks: Read on src/auth/jwt.ts delivers auth-samesite.md once, never blocks
    out1 = json.loads(run_hook('gate.js', {'session_id': 's1', 'tool_name': 'Read', 'tool_input': {'file_path': str(repo / 'src' / 'auth' / 'jwt.ts')}}))
    h1 = out1.get('hookSpecificOutput') or {}
    check('auth-samesite.md' in h1.get('additionalContext', '') and 'SameSite=Lax' in h1.get('additionalContext', ''), f'checks path-scoped missed: {out1!r}')
    check('permissionDecision' not in h1, f'path-scoped blocked a clean Read: {h1!r}')
    # Same note must not repeat on a second Edit in the same session, nor in router.js
    check(run_hook('gate.js', {'session_id': 's1', 'tool_name': 'Edit', 'tool_input': {'file_path': str(repo / 'src' / 'auth' / 'jwt.ts'), 'old_string': 'a', 'new_string': 'b'}}).strip() == '',
          'path-scoped repeated the same note in one session')
    check('auth-samesite.md' not in run_hook('router.js', {'session_id': 's1', 'prompt': 'cookie de sessao SameSite auth'}),
          'router repeated a note already delivered by path-scoped gate')
    # A separate worker (agent_id) still receives the file's note once
    w1 = json.loads(run_hook('gate.js', {'session_id': 's1', 'agent_id': 'builder1', 'tool_name': 'Read', 'tool_input': {'file_path': str(repo / 'src' / 'auth' / 'jwt.ts')}}))
    check('auth-samesite.md' in (w1.get('hookSpecificOutput') or {}).get('additionalContext', ''), f'worker did not get path-scoped note: {w1!r}')

    # 2. Path-scoped via paths: glob
    out2 = json.loads(run_hook('gate.js', {'session_id': 's2', 'tool_name': 'Edit', 'tool_input': {'file_path': str(repo / 'src' / 'ui' / 'modal.css'), 'old_string': 'a', 'new_string': 'b'}}))
    check('ui-zindex.md' in (out2.get('hookSpecificOutput') or {}).get('additionalContext', ''), f'paths glob missed: {out2!r}')
    # Unrelated file gets nothing
    check(run_hook('gate.js', {'session_id': 's2', 'tool_name': 'Read', 'tool_input': {'file_path': str(repo / 'README.md')}}).strip() == '',
          'path-scoped fired on unrelated file')

    # 3. BM25 + PT/EN stemming + 1-hop [[wikilink]]:
    # Prompt uses inflected words ("autenticando", "migrando") that old exact overlap missed!
    r_out = run_hook('router.js', {'session_id': 's3', 'prompt': 'estou autenticando e migrando o esquema'})
    check('db-migracao.md' in r_out, f'BM25 + stemmer missed inflected PT query: {r_out!r}')
    check('staging-ssh.md' in r_out and 'linked from [[db-migracao]]' in r_out, f'1-hop wikilink did not pull staging-ssh.md: {r_out!r}')

    # 4. Single accidental word must NOT trigger a note
    check(run_hook('router.js', {'session_id': 's4', 'prompt': 'ajusta o layout do botao azul'}).strip() == '',
          'BM25 false-triggered on unrelated prompt')

for e in errors:
    print('failed:', e)
print(f'{len(errors)} error(s)' if errors else 'PASS  test_memory_routing')
sys.exit(1 if errors else 0)
