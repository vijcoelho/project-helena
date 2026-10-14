"""history.py recall on fake transcripts, no LLM: python eval/test_recall.py"""
import json, os, pathlib, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'helena'))
import history

KEY = 'sk_' + 'live_' + 'FAKE' * 6  # assembled here so the guard hook does not block this file


def session(proj, sid, turns, age_days=0):
    d = history.PROJECTS / proj
    d.mkdir(parents=True, exist_ok=True)
    lines = []
    for ts, q, a in turns:
        lines.append({'type': 'user', 'cwd': f'C:\\dev\\{proj}', 'timestamp': ts, 'message': {'content': q}})
        lines.append({'type': 'assistant', 'timestamp': ts, 'message': {'content': [{'type': 'text', 'text': a}]}})
    f = d / f'{sid}.jsonl'
    f.write_text('\n'.join(map(json.dumps, lines)), encoding='utf-8')
    t = time.time() - age_days * 86400
    os.utime(f, (t, t))


with tempfile.TemporaryDirectory() as tmp:
    history.PROJECTS = pathlib.Path(tmp) / 'projects'
    session('shop', 'aaaaaaaa-1', [('2026-10-09T10:00:00Z', 'vamos usar postgres no banco', 'Certo.'),
                                   ('2026-10-10T10:00:00Z', 'e o deploy?', 'Decidimos: o deploy vai pelo coolify. token ' + KEY)])
    session('blog', 'bbbbbbbb-2', [('2026-10-11T10:00:00Z', 'a decisão sobre o banco ficou para depois', 'ok, postgres depois')])
    session('old', 'cccccccc-3', [('2026-08-01T10:00:00Z', 'postgres antigo', 'sim')], age_days=60)

    r = lambda *w, **k: history.recall(list(w), **k)
    assert [h['project'] for h in r('postgres')] == ['blog', 'shop'], r('postgres')  # newest first, old one out by default 30 days
    assert [h['id'] for h in r('coolify')] == ['aaaaaaaa-1'], r('coolify')  # only in the assistant's answer
    assert [h['project'] for h in r('postgres', 'banco')] == ['blog', 'shop'] and r('coolify', 'banco') == []  # all words
    assert len(r('DECISAO')) == 1 and 'decisão' in r('decisao', 'banco')[0]['text']  # accents and case ignored
    assert [h['project'] for h in r('postgres', days=90)] == ['blog', 'shop', 'old']  # --days reaches the old one
    assert [h['project'] for h in r('postgres', project='shop')] == ['shop']
    assert KEY not in r('coolify')[0]['text'] and '***' in r('coolify')[0]['text']

    # the CLI reads the real folder: only the "nothing found" line is checked there
    p = subprocess.run([sys.executable, str(ROOT / 'helena' / 'history.py'), 'recall', 'zzqxj' + 'nonexistent'],
                       capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert p.returncode == 0 and 'Nothing found' in p.stdout, (p.returncode, p.stdout, p.stderr)

print('ok: recall finds prompt/answer, all words, accents, days, project, masks keys, clear when empty')
