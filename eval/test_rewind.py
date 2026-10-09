"""Undo for any CLI and the done check, no LLM: python eval/test_rewind.py

rewind: router.js snapshots the folder before a request; rewinding brings back the edited file, removes the file the AI
created, leaves the index alone, and rewinding again undoes the rewind.
done: when this turn edited code and the tests fail, the Stop hook sends the failure back once; it stays quiet when the
tests pass, when nothing was edited this turn, and when .helena/test says off.
"""
import json, os, pathlib, subprocess, sys, tempfile

HOOKS = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)


with tempfile.TemporaryDirectory() as tmp:
    t = pathlib.Path(tmp)
    repo, home = t / 'repo', t / 'home'
    repo.mkdir(), home.mkdir()
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home), HELENA_VAULT=str(t / 'vault'))
    git = lambda *a: subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *a], cwd=repo, check=True,
                                    capture_output=True, text=True).stdout
    (repo / 'a.txt').write_text('v1\n')
    git('init', '-q'); git('add', '.'); git('commit', '-qm', 'init')
    (repo / 'notes.txt').write_text('untracked, mine\n')

    prompt = lambda p: subprocess.run(['node', str(HOOKS / 'router.js')], input=json.dumps({'prompt': p, 'session_id': 's', 'cwd': str(repo)}),
                                      cwd=repo, env=env, capture_output=True, text=True, timeout=30)
    rewind = lambda *a: subprocess.run(['node', str(HOOKS / 'rewind.js'), *a], cwd=repo, env=env, capture_output=True, text=True, timeout=30).stdout

    prompt('refactor the parser')                     # snapshot: a.txt v1 + notes.txt
    (repo / 'a.txt').write_text('v2 broken\n')        # what the AI did
    (repo / 'b.txt').write_text('new file\n')
    git('add', 'a.txt')                               # something staged, to see the index is left alone
    check('refactor the parser' in rewind(), 'list does not show the request:\n' + rewind())
    out = rewind('1')
    check((repo / 'a.txt').read_text() == 'v1\n' and not (repo / 'b.txt').exists(), 'rewind did not restore: ' + out)
    check((repo / 'notes.txt').exists(), 'rewind removed an untracked file that was already there')
    check('a.txt' in git('diff', '--cached', '--name-only'), 'rewind touched the index')
    rewind('1')
    check((repo / 'a.txt').read_text() == 'v2 broken\n' and (repo / 'b.txt').exists(), 'rewinding again did not undo the rewind')
    check('no snapshot' in rewind('9'), 'asking too far back should say so')

    # ---- done check
    proj = t / 'proj'
    proj.mkdir()
    (proj / 'package.json').write_text(json.dumps({'scripts': {'test': 'node test.js'}}))
    (proj / 'sum.js').write_text('module.exports = (a, b) => a - b\n')
    (proj / 'test.js').write_text("if (require('./sum')(2, 2) !== 4) { console.error('sum(2,2) should be 4'); process.exit(1) }\n")

    def transcript(edit_after_user=True):
        lines = [{'type': 'user', 'message': {'content': 'fix sum'}}]
        edit = {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Edit', 'input': {'file_path': str(proj / 'sum.js')}}]}}
        lines = lines + [edit] if edit_after_user else [edit] + lines
        f = t / f'tr-{edit_after_user}.jsonl'
        f.write_text('\n'.join(json.dumps(l) for l in lines) + '\n')
        return str(f)

    def stop(tr, active=False):
        r = subprocess.run(['node', str(HOOKS / 'done.js')], input=json.dumps({'transcript_path': tr, 'cwd': str(proj), 'stop_hook_active': active}),
                           cwd=proj, env=env, capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.stdout.strip() else {}

    out = stop(transcript())
    check(out.get('decision') == 'block' and 'sum(2,2) should be 4' in out.get('reason', ''), 'failing tests did not block: ' + str(out))
    check(not stop(transcript(), active=True), 'blocked twice in the same turn')
    check(not stop(transcript(edit_after_user=False)), 'blocked although nothing was edited this turn')
    (proj / '.helena').mkdir()
    (proj / '.helena' / 'test').write_text('off\n')
    check(not stop(transcript()), '.helena/test off was ignored')
    (proj / '.helena' / 'test').unlink()
    (proj / 'sum.js').write_text('module.exports = (a, b) => a + b\n')
    check(not stop(transcript()), 'passing tests blocked')

for e in errors:
    print('failed:', e)
print('ok: rewind restores and undoes itself; done check blocks only failing code turns' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
