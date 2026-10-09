"""Plan-limit warning and weekly pace, no LLM: python eval/test_limits.py

In a fake home where Claude used 96% and Codex 3%, a Claude prompt gets "write HANDOFF.md, continue in codex" with the
command ready to paste, only once per session; a Codex prompt (transcript under .codex) gets nothing.
Then a week where 60% went in 2 days: the pace warning says it runs out before the reset, once a day.
"""
import json, os, pathlib, shutil, subprocess, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
assert shutil.which('claude') and shutil.which('codex'), 'needs both CLIs on PATH'
now = int(time.time())
later = now + 3600

with tempfile.TemporaryDirectory() as home:
    h = pathlib.Path(home)
    (h / '.helena').mkdir()
    limits = h / '.helena' / 'limits-claude.json'
    limits.write_text(json.dumps(
        {'five_hour': {'used_percentage': 96, 'resets_at': later}, 'seven_day': {'used_percentage': 40, 'resets_at': later}}))
    day = h / '.codex' / 'sessions' / '2026' / '10' / '06'
    day.mkdir(parents=True)
    (day / 'rollout-x.jsonl').write_text(json.dumps({'type': 'event_msg', 'payload': {'type': 'token_count', 'rate_limits': {
        'primary': {'used_percent': 3.0, 'resets_at': later}, 'secondary': {'used_percent': 1.0, 'resets_at': later}}}}) + '\n')
    env = dict(os.environ, USERPROFILE=home, HOME=home, HELENA_EVAL='1', HELENA_VAULT=str(h / 'vault'))

    def prompt(transcript, session='s1'):
        ev = {'prompt': 'continua o trabalho', 'session_id': session, 'cwd': home, 'transcript_path': transcript}
        return subprocess.run(['node', str(ROOT / 'helena' / 'hooks' / 'router.js')], input=json.dumps(ev),
                              capture_output=True, text=True, encoding='utf-8', env=env, timeout=30).stdout

    first = prompt(str(h / '.claude' / 'projects' / 'x' / 's1.jsonl'))
    assert 'Claude has used 96%' in first and 'HANDOFF.md' in first and '`codex` (Codex, 3% used)' in first, first
    assert '`codex "Read HANDOFF.md and continue from Next"`' in first, 'no ready-to-paste command:\n' + first
    assert 'Claude has used' not in prompt(str(h / '.claude' / 'projects' / 'x' / 's1.jsonl')), 'warned twice'
    assert 'has used' not in prompt(str(day / 'rollout-x.jsonl'), 's2'), 'Codex has room, no warning expected'

    # 60% of the week gone after 2 of 7 days: at that rate it runs out in ~1.3 days, long before the reset in 5
    limits.write_text(json.dumps({'five_hour': {'used_percentage': 10, 'resets_at': later},
                                  'seven_day': {'used_percentage': 60, 'resets_at': now + 5 * 86400}}))
    paced = prompt(str(h / '.claude' / 'projects' / 'x' / 's3.jsonl'), 's3')
    assert 'weekly limit' in paced and 'runs out' in paced and '% a day lasts the week' in paced, 'no pace warning:\n' + paced
    assert 'weekly limit' not in prompt(str(h / '.claude' / 'projects' / 'x' / 's4.jsonl'), 's4'), 'pace warned twice in a day'
    report = subprocess.run(['node', str(ROOT / 'helena' / 'hooks' / 'limits.js')], capture_output=True, text=True, env=env).stdout
    assert 'week 60%' in report and 'runs out' in report and 'Codex' in report, report

print('ok: limit warning names the free AI with a ready command, once per session; weekly pace warns once a day')
