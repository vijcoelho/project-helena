"""The status line, no LLM: context size, until when the cache of it lives, and a model switch that will not find it.

    python eval/test_statusline.py
"""
import datetime, json, os, pathlib, subprocess, sys, tempfile

LINE = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'statusline.js'
errors = []

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    env = dict(os.environ, USERPROFILE=str(tmp), HOME=str(tmp))
    (tmp / '.helena').mkdir()

    def line(calls, model='claude-opus-5-5'):
        """calls: (minutes ago, tokens read from the cache, {what the call wrote to the cache})"""
        f = tmp / 't.jsonl'
        f.write_text('\n'.join(json.dumps({'type': 'assistant', 'timestamp': (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=ago)).isoformat().replace('+00:00', 'Z'), 'message': {'model': said, 'content': [], 'usage': {
                'input_tokens': 5, 'cache_read_input_tokens': read, 'cache_creation_input_tokens': 0, 'cache_creation': made}}})
            for ago, read, made, said in calls) + '\n')
        return subprocess.run(['node', str(LINE)], input=json.dumps({'transcript_path': str(f), 'model': {'id': model, 'display_name': 'Opus'}}),
                              capture_output=True, text=True, encoding='utf-8', env=env).stdout

    hour, five, none, opus = {'ephemeral_1h_input_tokens': 900}, {'ephemeral_5m_input_tokens': 900}, {}, 'claude-opus-5-5'
    clock = lambda minutes: (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).strftime('%H:%M')
    # the transcript was written a moment before this is asked: the minute may have turned in between
    until = lambda out, minutes: any(f'cache until {clock(m)}' in out for m in (minutes, minutes - 1))

    out = line([(10, 90000, hour, opus), (2, 130000, none, opus)])  # the last call wrote nothing: the life comes from the one before
    if 'ctx 130k' not in out or not until(out, 58):
        errors.append(f'1 hour cache, last call 2 minutes ago: {out}')
    out = line([(2, 60000, five, opus)])
    if not until(out, 3):
        errors.append(f'5 minute cache: {out}')
    if 'cache expired' not in line([(9, 60000, five, opus)]):
        errors.append('a 5 minute cache read 9 minutes later is not said to be gone')
    if 'cache' in line([(2, 9000, five, opus)]):
        errors.append('a 9k context: nothing worth a line')
    out = line([(1, 80000, hour, 'claude-sonnet-5-5')])
    if 'model changed: next message re-reads 80k uncached' not in out:
        errors.append(f'Sonnet answered, Opus is selected: {out}')
    if 'model changed' in line([(1, 80000, hour, opus)], model='claude-opus-5-5[1m]'):
        errors.append('the same model under a longer id read as a switch')
    out = line([(3, 80000, hour, opus), (1, 0, none, '<synthetic>')])  # an error line written by the CLI is not a call
    if 'ctx 80k' not in out or 'model changed' in out:
        errors.append(f'a synthetic line was read as the last call: {out}')

for e in errors:
    print('failed:', e)
print('ok: context, cache until, cache expired, model switch' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
