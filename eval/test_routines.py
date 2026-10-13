"""Tests v0.9 routines without any LLM call: add/validate, due check, run log, "needs you" and goal progress.

    python eval/test_routines.py
"""
import json, pathlib, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'helena'))
import history, routines, worker

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    history.HOME = worker.HOME = tmp / '.helena'
    routines.FILE = tmp / '.helena' / 'routines.json'
    routines.VAULT = vault = tmp / 'vault'
    project = tmp / 'shop'
    project.mkdir()

    for bad in ({'name': 'x', 'prompt': 'p', 'every': 'weekly'}, {'name': 'x', 'prompt': '', 'every': '1d'},
                {'name': 'x', 'prompt': 'p', 'every': '1d', 'project': str(tmp / 'nope')}):
        try:
            routines.main(['add', json.dumps(bad)])
            raise AssertionError(f'accepted {bad}')
        except ValueError:
            pass
    routines.main(['add', json.dumps({'name': 'Deps Check', 'prompt': 'check deps', 'every': '7d',
                                      'project': str(project), 'goal': 'all deps current'})])
    saved = json.loads(routines.FILE.read_text(encoding='utf-8'))
    assert [r['name'] for r in saved] == ['deps-check'], saved

    calls = []
    def fake_run(cmd, **kw):
        calls.append((cmd, kw))
        result = 'Two deps are old.\nNEEDS YOU: upgrade react 18 to 19?\nPROGRESS: 8 of 10 current'
        return subprocess.CompletedProcess(cmd, 0, json.dumps({'result': result, 'total_cost_usd': 0.02}), '')
    routines.subprocess.run = fake_run

    routines.run_due()
    routines.run_due()  # not due again for 7 days
    assert len(calls) == 1, calls
    cmd, kw = calls[0]
    assert cmd[cmd.index('--tools') + 1] == routines.TOOLS and cmd[cmd.index('--max-budget-usd') + 1] == '0.1', cmd
    assert kw['cwd'] == str(project) and 'all deps current' in kw['input'] and 'NEEDS YOU:' in kw['input']

    log = (vault / 'Routines' / 'deps-check.md').read_text(encoding='utf-8')
    assert 'Two deps are old.' in log and '($0.020)' in log, log
    assert '- [ ] ' in (vault / 'Inbox' / 'needs-you.md').read_text(encoding='utf-8')
    news = json.loads((tmp / '.helena' / 'news.json').read_text(encoding='utf-8'))
    assert 'upgrade react 18 to 19?' in news[0], news
    assert 'routine deps-check: 8 of 10 current' in (vault / 'Projects' / 'shop.md').read_text(encoding='utf-8')
    assert 'routine:deps-check' in (tmp / '.helena' / 'ledger.jsonl').read_text(encoding='utf-8')

    routines.main(['remove', 'deps-check'])
    assert json.loads(routines.FILE.read_text(encoding='utf-8')) == []

    # ready-made routines: a script collects the facts, the model is only called when they are new
    try:
        routines.main(['add', json.dumps({'name': 'x', 'prompt': 'p', 'every': '1d', 'gather': 'nope'})])
        raise AssertionError('accepted an unknown gather')
    except ValueError:
        pass
    routines.shutil.which = lambda tool: tool
    routines.main(['add', 'ci', str(project)])
    saved = json.loads(routines.FILE.read_text(encoding='utf-8'))
    assert saved[0]['name'] == 'ci-shop' and saved[0]['gather'] == 'ci' and saved[0]['every'] == '12h', saved
    facts = ['', 'tests on main (run 7):\nFAIL cart.test.js key ' + 'sk_' + 'live_' + 'X9' * 12, 'tests on main (run 7):\nFAIL cart.test.js key ' + 'sk_' + 'live_' + 'X9' * 12]
    routines.GATHER['ci'] = lambda cwd: facts.pop(0)
    del calls[:]
    for _ in range(3):  # green CI, a failing run, the same failing run again
        routines.main(['run', 'ci-shop'])
    assert len(calls) == 1, f'{len(calls)} model calls for one new failure'
    sent = calls[0][1]['input']
    assert '<facts>' in sent and 'FAIL cart.test.js' in sent and 'X9X9' not in sent and 'NEEDS YOU:' in sent, sent

    # the two collectors, on canned tool output
    def tool(cmd, **kw):
        if 'outdated' in cmd:
            out = {'react': {'current': '18.3.1', 'wanted': '18.3.1', 'latest': '19.2.0'}, 'lodash': {'current': '4.17.20', 'latest': '4.17.21'}}
        elif 'list' in cmd:
            out = [{'databaseId': 9, 'conclusion': 'success', 'workflowName': 'tests', 'headBranch': 'main', 'displayTitle': 'fix'},
                   {'databaseId': 8, 'conclusion': 'failure', 'workflowName': 'tests', 'headBranch': 'main', 'displayTitle': 'old'},
                   {'databaseId': 7, 'conclusion': 'failure', 'workflowName': 'lint', 'headBranch': 'main', 'displayTitle': 'style'}]
        else:
            return subprocess.CompletedProcess(cmd, 1, 'line\n' * 200 + 'error: unused variable', '')
        return subprocess.CompletedProcess(cmd, 1, json.dumps(out), '')
    routines.subprocess.run = tool
    assert routines.deps(str(project)) == 'react: 18.3.1 -> 19.2.0', routines.deps(str(project))
    got = routines.ci(str(project))
    assert 'lint on main (style, run 7)' in got and 'unused variable' in got and 'run 8' not in got and got.count('\n') < 70, got

print('PASS  test_routines')
