"""Plan-limit warning, no LLM: python eval/test_limits.py

In a fake home where Claude used 96% and Codex 3%, a Claude prompt gets "write HANDOFF.md, continue in codex",
only once per session; a Codex prompt (transcript under .codex) gets nothing.
"""
import json, os, pathlib, shutil, subprocess, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
assert shutil.which('claude') and shutil.which('codex'), 'needs both CLIs on PATH'
later = int(time.time()) + 3600

with tempfile.TemporaryDirectory() as home:
    h = pathlib.Path(home)
    (h / '.helena').mkdir()
    (h / '.helena' / 'limits-claude.json').write_text(json.dumps(
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
    assert 'Claude has used' not in prompt(str(h / '.claude' / 'projects' / 'x' / 's1.jsonl')), 'warned twice'
    assert 'has used' not in prompt(str(day / 'rollout-x.jsonl'), 's2'), 'Codex has room, no warning expected'

print('ok: limit warning names the free AI, once per session, silent when there is room')
