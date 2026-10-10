"""Tests the budget report's reading of transcripts, no LLM: one API call counted once, subagents listed by model.

    python eval/test_budget.py
"""
import json, os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'helena'))
import history

call = lambda mid, model, read: json.dumps({'type': 'assistant', 'timestamp': '2026-10-09T10:00:00Z', 'cwd': 'C:/dev/shop', 'message': {
    'id': mid, 'model': model, 'content': [], 'usage': {'input_tokens': 10, 'cache_read_input_tokens': read, 'output_tokens': 5}}})

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    history.PROJECTS = tmp / '.claude' / 'projects'
    sub = history.PROJECTS / 'shop' / 's1' / 'subagents'
    sub.mkdir(parents=True)
    # Claude Code writes one line per content block of the same call, each with the same usage
    (history.PROJECTS / 'shop' / 's1.jsonl').write_text('\n'.join([call('m1', 'claude-opus-5-5', 1000)] * 3 + [call('m2', 'claude-opus-5-5', 2000)]))
    (sub / 'agent-a1.jsonl').write_text('\n'.join([call('w1', 'claude-haiku-5-5', 150000)] * 2 + [call('w2', 'claude-haiku-5-5', 50000)]))
    (sub / 'agent-a1.meta.json').write_text(json.dumps({'agentType': 'scout', 'description': 'find the routes', 'model': 'haiku', 'effort': 'max'}))

    main, = history.sessions(7)
    assert [u['read'] for u in main['usage']] == [1000, 2000], main['usage']
    worker, = history.subagents(7)
    assert len(worker['usage']) == 2 and worker['meta']['effort'] == 'max', worker

    out = subprocess.run([sys.executable, str(ROOT / 'helena' / 'budget.py')], capture_output=True, text=True, encoding='utf-8',
                         env=dict(os.environ, USERPROFILE=str(tmp), HOME=str(tmp))).stdout
    assert '1 sessions, 3k tokens' in out, out
    line = next(l for l in out.splitlines() if l.strip().startswith('haiku-5-5'))
    assert line.split() == ['haiku-5-5', 'max', '1', '2', '200k', '1'], line  # 1 worker, 2 calls, 1 of them over 100k
    assert 'scout: find the routes' in out, out

print('PASS  test_budget')
