"""Tests v1.0 tidy without any LLM call: memory merge + archive + relinking, stale flags, folding lessons + undo, weekly note.

    python eval/test_tidy.py
"""
import datetime, json, pathlib, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'helena'))
import skills, tidy, worker

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    home, vault, lib = tmp / '.helena', tmp / 'vault', tmp / '.helena' / 'library'
    worker.HOME = tidy.HOME = home
    tidy.STATE = home / 'tidy.json'
    skills.LIB = lib
    memory = vault / 'Memory'
    memory.mkdir(parents=True)
    note = lambda name, body: (memory / f'{name}.md').write_text(f'---\ntype: rule\ndescription: {name}\n---\n{body}\n', encoding='utf-8')  # noqa: E731
    note('roadmap', 'no SQL')
    note('no-sql', 'never SQL or Docker')
    note('other', 'see [[no-sql]]')
    note('old-plan', 'ship v0.5 tomorrow')

    calls = []
    def fake(prompt, what):
        calls.append(what)
        if what == 'tidy-memory':
            return {'merge': [{'keep': 'roadmap', 'drop': ['no-sql'], 'description': 'no SQL, no Docker', 'body': 'No SQL, no Docker.'}],
                    'stale': [{'slug': 'old-plan', 'why': 'v0.5 shipped'}, {'slug': 'ghost', 'why': 'x'}]}
        return {'skill': '# Video\n\n## Steps\n- render at 30fps\n'}
    tidy.ask = fake

    md = lib / 'video' / 'SKILL.md'
    md.parent.mkdir(parents=True)
    today = datetime.date.today().isoformat()
    original = '---\nname: video\n---\n# Video\n\n## Steps\n- render\n\n## Learned\n' + ''.join(f'- {today}: lesson {i}\n' for i in range(5))
    md.write_text(original, encoding='utf-8')

    week = tidy.main(vault, lib)
    kept = (memory / 'roadmap.md').read_text(encoding='utf-8')
    assert 'description: no SQL, no Docker' in kept and 'No SQL, no Docker.' in kept and 'type: rule' in kept, kept
    assert not (memory / 'no-sql.md').exists()
    assert sorted(p.name[11:] for p in (vault / 'Archive').iterdir()) == ['no-sql.md', 'roadmap.md']
    assert '[[roadmap]]' in (memory / 'other.md').read_text(encoding='utf-8')
    news = json.loads((home / 'news.json').read_text(encoding='utf-8'))
    assert any('old-plan' in n for n in news) and not any('ghost' in n for n in news), news

    text = week.read_text(encoding='utf-8')
    assert '[[roadmap]]' in text and 'lesson 4' in text, text  # folded lessons still show up in the week

    assert md.read_text(encoding='utf-8') == '---\nname: video\n---\n# Video\n\n## Steps\n- render at 30fps\n'
    skills.unfold('video')
    assert md.read_text(encoding='utf-8') == original

    # nothing changed in Memory since: no second LLM call for hygiene
    calls.clear()
    tidy.main(vault, lib)
    assert calls == ['tidy-skill'], calls  # the restored skill still has 5 lessons, so it is offered again

print('PASS  test_tidy')
