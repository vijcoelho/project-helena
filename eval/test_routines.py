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

print('PASS  test_routines')
