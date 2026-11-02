"""November checks: loop cut (gate.js), post-edit test reminder (nudge.js), tests weakened and receipts (done.js),
the user's rules after a compaction (start.js). No LLM: python eval/test_receipts.py
"""
import json, os, pathlib, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / 'helena' / 'hooks'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)


def node(script, cwd, env, ev):
    return subprocess.run(['node', str(HOOKS / script)], input=json.dumps(ev), cwd=cwd, capture_output=True,
                          text=True, encoding='utf-8', env=env, timeout=60).stdout


def transcript(path, entries):
    """entries: ('user', text) | ('say', text) | ('tool', id, name, input, result, is_error)"""
    lines = []
    for e in entries:
        if e[0] == 'user':
            lines.append({'type': 'user', 'message': {'role': 'user', 'content': e[1]}})
        elif e[0] == 'say':
            lines.append({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': e[1]}]}})
        else:
            _, i, name, inp, res, err = e
            lines.append({'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': i, 'name': name, 'input': inp}]}})
            lines.append({'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': i, 'content': res, 'is_error': err}]}})
    path.write_text('\n'.join(json.dumps(x) for x in lines) + '\n', encoding='utf-8')
    return str(path)


with tempfile.TemporaryDirectory() as tmp:
    t = pathlib.Path(tmp)
    home, repo = t / 'home', t / 'repo'
    (home / '.helena').mkdir(parents=True)
    repo.mkdir()
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home), HELENA_VAULT=str(t / 'vault'), HELENA_EVAL='1')
    git = lambda *a: subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *a], cwd=repo, check=True, capture_output=True)
    (repo / 'calc.py').write_text('def add(a, b):\n    return a + b\n')
    (repo / 'test_calc.py').write_text('from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n    assert add(0, 0) == 0\n')
    git('init', '-q'); git('add', '.'); git('commit', '-qm', 'init')
    T = t / 't.jsonl'

    # loop: 4 identical calls with identical results, the 5th is denied; a poll whose output changes is not
    cmd = {'command': 'curl localhost:3000'}
    gate = lambda entries: node('gate.js', repo, env, {'tool_name': 'Bash', 'tool_input': cmd, 'cwd': str(repo),
                                                        'transcript_path': transcript(T, entries)})
    same = [('tool', f'c{i}', 'Bash', cmd, 'connection refused', True) for i in range(4)]
    out = gate([('user', 'start the server'), *same])
    check('Helena / loop' in out, f'gate: 4 same calls + same result not denied: {out!r}')
    out = gate([('user', 'start the server'), *[('tool', f'c{i}', 'Bash', cmd, f'waiting {i}', True) for i in range(4)]])
    check('loop' not in out, f'gate: a poll with changing output was denied: {out!r}')
    out = gate([*same, ('user', 'try again')])
    check('loop' not in out, f'gate: calls from before the user message counted: {out!r}')

    (repo / '.helena').mkdir()
    (repo / '.helena' / 'test').write_text('python -m pytest -q\n')
    # nudge: the 3rd code edit with no test run in between gets one line; a test run resets the count
    ed = lambda i: ('tool', f'e{i}', 'Edit', {'file_path': str(repo / 'calc.py')}, 'ok', False)
    ev = {'tool_name': 'Edit', 'tool_input': {'file_path': str(repo / 'calc.py')}, 'cwd': str(repo)}
    out = node('nudge.js', repo, env, {**ev, 'transcript_path': transcript(T, [('user', 'x'), ed(1), ed(2), ed(3)])})
    check('3 code edits' in out and 'pytest' in out, f'nudge: no reminder after 3 edits: {out!r}')
    out = node('nudge.js', repo, env, {**ev, 'transcript_path': transcript(T, [('user', 'x'), ed(1), ed(2)])})
    check(out.strip() == '', f'nudge: reminded after 2 edits: {out!r}')
    run = ('tool', 'r1', 'Bash', {'command': 'python -m pytest -q'}, 'ok', False)
    out = node('nudge.js', repo, env, {**ev, 'transcript_path': transcript(T, [('user', 'x'), ed(1), ed(2), run, ed(3)])})
    check(out.strip() == '', f'nudge: a test run did not reset the count: {out!r}')
    (repo / '.helena' / 'test').unlink()

    # weakened: an assertion removed outside the gate (a sed) blocks once at Stop, even with the tests green
    (repo / 'calc.py').write_text('def add(a, b):\n    return b + a\n')
    (repo / 'test_calc.py').write_text('from calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n')
    edit = ('tool', 'e1', 'Edit', {'file_path': str(repo / 'calc.py')}, 'ok', False)
    stop = {'cwd': str(repo), 'session_id': 's', 'transcript_path': transcript(T, [('user', 'fix'), edit, ('say', 'done')])}
    out = node('done.js', repo, env, stop)
    check('tests weakened' in out and 'test_calc.py' in out, f'done: removed assertion not caught: {out!r}')
    out = node('done.js', repo, env, stop)
    check('tests weakened' not in out, f'done: same weakening blocked twice: {out!r}')
    git('checkout', '--', '.')

    # receipts (no test command here): "tests pass" with no test run after the last edit blocks; a green run does not
    (repo / 'test_calc.py').unlink(); git('commit', '-qam', 'no tests')
    (repo / 'calc.py').write_text('def add(a, b):\n    return a + b + 0\n')
    done = lambda entries: node('done.js', repo, env, {**stop, 'transcript_path': transcript(T, entries)})
    out = done([('user', 'fix'), edit, ('say', 'Fixed. All tests pass.')])
    check('Helena / receipt' in out and 'no test ran' in out, f'done: unbacked "tests pass" not caught: {out!r}')
    out = done([('user', 'fix'), edit, ('tool', 'r2', 'Bash', {'command': 'node --test'}, 'ok', False), ('say', 'Fixed. Tests pass.')])
    check('receipt' not in out, f'done: a backed claim was blocked: {out!r}')
    notes = ('tool', 'e2', 'Edit', {'file_path': str(repo / 'NOTES.md')}, 'ok', False)
    out = done([('user', 'fix'), edit, ('tool', 'r4', 'Bash', {'command': 'python eval/test_calc.py'}, 'ok', False), notes,
                ('say', 'All tests pass.')])
    check('receipt' not in out, f'done: a test_*.py run, or a later non-code edit, broke the receipt: {out!r}')
    out = done([('user', 'fix'), edit, ('tool', 'r3', 'Bash', {'command': 'node --test'}, 'Exit code 1', True),
                ('say', 'Fixed, the tests are passing now.')])
    check('Helena / receipt' in out and 'failed' in out, f'done: claim after a red run not caught: {out!r}')
    out = done([('user', 'fix'), edit, ('say', "Fixed, but the tests don't pass yet.")])
    check('receipt' not in out, f'done: a negated claim was blocked: {out!r}')

    # compaction: the user's rules from before it come back word for word, other chatter does not
    out = node('start.js', repo, env, {'source': 'compact', 'cwd': str(repo), 'transcript_path': transcript(T, [
        ('user', 'Build the login page. Never touch config/prod.yaml.'), ('say', 'ok'),
        ('user', '<command-name>/clear</command-name>'), ('user', 'nice work there'),
        ('user', 'Não use internet nessa tarefa.')])})
    check('Never touch config/prod.yaml.' in out and 'Não use internet nessa tarefa.' in out, f'start: rules not re-pinned: {out[-600:]!r}')
    check('nice work' not in out and 'command-name' not in out, 'start: chatter or command text re-pinned')
    out = node('start.js', repo, env, {'source': 'startup', 'cwd': str(repo), 'transcript_path': str(T)})
    check('just compacted' not in out, 'start: rules re-pinned on a normal startup')

print('\n'.join(errors) or 'ok')
raise SystemExit(1 if errors else 0)
