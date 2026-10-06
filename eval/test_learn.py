"""Tests v0.8 without any LLM call: checkpoint offsets, used-skill detection, "## Learned" lines and their undo.

    python eval/test_learn.py
"""
import json, pathlib, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'helena'))
import distill, skills

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    distill.LIB = skills.LIB = tmp / '.helena' / 'library'
    distill.STATE = tmp / 'distilled.json'
    md = distill.LIB / 'video-demo' / 'SKILL.md'
    md.parent.mkdir(parents=True)
    md.write_text('---\nname: video-demo\n---\n# Video\n\n## Gotchas\n- x\n', encoding='utf-8')

    # learned lines land in their own section, in order, and undo drops only the last one
    distill.learn(md, '- 2026-10-06: one')
    distill.learn(md, '- 2026-10-07: two')
    assert md.read_text(encoding='utf-8').endswith('## Gotchas\n- x\n\n## Learned\n- 2026-10-06: one\n- 2026-10-07: two\n'), md.read_text()
    md.write_text(md.read_text(encoding='utf-8') + '\n## After\nkeep\n', encoding='utf-8')
    distill.learn(md, '- 2026-10-08: three')
    assert '- 2026-10-07: two\n- 2026-10-08: three\n\n## After\nkeep' in md.read_text(encoding='utf-8'), md.read_text()
    skills.unlearn('video-demo')
    text = md.read_text(encoding='utf-8')
    assert 'three' not in text and 'two' in text and '## After\nkeep' in text, text

    # a skill counts as used only when the assistant opened it, not when a hook listed its path
    t = tmp / 's.jsonl'
    lines = [{'type': 'user', 'message': {'content': f'prompt {i}'}} for i in range(7)]
    lines.insert(1, {'type': 'user', 'message': {'content': 'Read before coding: ~/.helena/library/other/SKILL.md'}})
    lines.insert(2, {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Read',
                     'input': {'file_path': str(md)}}]}})
    t.write_text('\n'.join(json.dumps(l) for l in lines), encoding='utf-8')
    assert distill.used_skills(t) == ['video-demo'], distill.used_skills(t)

    # checkpoint: first run reads every turn, the next only the new ones, a run with nothing new asks nothing
    seen = []
    distill.ask = lambda p: seen.append(p) or {}
    sys.argv = ['distill.py', str(t), str(tmp / 'vault')]
    distill.main()
    distill.main()
    with open(t, 'a', encoding='utf-8') as f:
        f.write('\n' + json.dumps({'type': 'user', 'message': {'content': 'prompt NEW'}}))
    distill.main()
    assert len(seen) == 2 and 'prompt 0' in seen[0] and 'prompt NEW' in seen[1] and 'prompt 0' not in seen[1], seen
    assert 'SKILLS USED THIS SESSION: video-demo' in seen[0]

    # the model can only teach a skill that was used
    distill.write({'learned': [{'skill': 'video-demo', 'lesson': 'ok'}, {'skill': 'other', 'lesson': 'no'}]},
                  tmp / 'vault', 's', used=['video-demo'])
    assert md.read_text(encoding='utf-8').count(': ok') == 1

print('PASS  test_learn')
