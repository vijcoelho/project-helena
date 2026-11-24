"""Tests Phase 2 lifecycle hooks (PreModelSwitch, StopFailure, PostToolUseFailure) and gate.js Code Mode chaining nudge.

    python eval/test_lifecycle.py
"""
import datetime, json, os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)


with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    home, d = tmp / 'home', tmp / 'shop'
    (home / '.helena').mkdir(parents=True)
    (home / 'vault' / 'Memory').mkdir(parents=True)
    d.mkdir()
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home), HELENA_EVAL='1', HELENA_VAULT=str(home / 'vault'))

    def hook(script, ev, raw=False):
        r = subprocess.run(['node', str(ROOT / script)], input=json.dumps({'cwd': str(d), 'session_id': 'life1', **ev}),
                           capture_output=True, text=True, encoding='utf-8', env=env, cwd=d, timeout=30)
        return r.stdout if raw else (json.loads(r.stdout) if r.stdout.strip() else {})

    # 1. PreModelSwitch: warns when >= 40k warm cache would be dropped; silent when cold or small or same model
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    old_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=15)).isoformat().replace('+00:00', 'Z')
    tr_warm = d / 'warm.jsonl'
    tr_warm.write_text(json.dumps({
        'type': 'assistant', 'timestamp': now_iso,
        'message': {'model': 'claude-opus-5-5', 'usage': {
            'input_tokens': 10, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 85000,
            'cache_creation': {'ephemeral_5m_input_tokens': 5000}
        }}
    }) + '\n', encoding='utf-8')
    out = hook('lifecycle.js', {'hook_event_name': 'PreModelSwitch', 'transcript_path': str(tr_warm), 'to_model': 'claude-sonnet-5-5'})
    ctx = (out.get('hookSpecificOutput') or {}).get('additionalContext', '')
    check('85k of warm prompt cache' in ctx and 'HANDOFF.md' in ctx, f'PreModelSwitch warm did not warn: {out!r}')
    check(hook('lifecycle.js', {'hook_event_name': 'PreModelSwitch', 'transcript_path': str(tr_warm), 'to_model': 'claude-opus-5-5'}) == {},
          'PreModelSwitch warned on same model')
    tr_cold = d / 'cold.jsonl'
    tr_cold.write_text(tr_warm.read_text(encoding='utf-8').replace(now_iso, old_iso), encoding='utf-8')
    check(hook('lifecycle.js', {'hook_event_name': 'PreModelSwitch', 'transcript_path': str(tr_cold), 'to_model': 'claude-sonnet-5-5'}) == {},
          'PreModelSwitch warned on expired cache')

    # 2. StopFailure: rate limit prints actionable handoff line and logs event; non-limit error stays quiet
    msg = hook('lifecycle.js', {'hook_event_name': 'StopFailure', 'error': '429 rate_limit exceeded'}, raw=True)
    check('HANDOFF.md' in msg or 'limit' in msg.lower(), f'StopFailure rate limit stayed silent: {msg!r}')
    events = [json.loads(l) for l in (home / '.helena' / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
    check(any(e.get('kind') == 'stop_failure' for e in events), 'StopFailure was not logged in events.jsonl')
    check(hook('lifecycle.js', {'hook_event_name': 'StopFailure', 'error': 'socket hang up'}, raw=True).strip() == '',
          'StopFailure printed limit hint for non-limit error')

    # 3. PostToolUseFailure: matches error_pattern note once per signature/session, skips interrupts
    (home / 'vault' / 'Memory' / 'fix-ebusy.md').write_text(
        '---\ntype: rule\ndescription: Windows EBUSY lock on node_modules\nproject: shop\nerror_pattern: EBUSY.*unlink\n---\n'
        'Close the dev server before running npm ci on Windows.\n', encoding='utf-8'
    )
    f1 = hook('lifecycle.js', {'hook_event_name': 'PostToolUseFailure', 'tool_name': 'Bash', 'error': 'Error: EBUSY: resource busy or locked, unlink node_modules'})
    fctx = (f1.get('hookSpecificOutput') or {}).get('additionalContext', '')
    check('fix-ebusy.md' in fctx and 'Close the dev server' in fctx, f'PostToolUseFailure missed error_pattern: {f1!r}')
    check(hook('lifecycle.js', {'hook_event_name': 'PostToolUseFailure', 'tool_name': 'Bash', 'error': 'Error: EBUSY: resource busy or locked, unlink node_modules'}) == {},
          'PostToolUseFailure repeated the same hint in one session')
    check(hook('lifecycle.js', {'hook_event_name': 'PostToolUseFailure', 'tool_name': 'Bash', 'is_interrupt': True, 'error': 'Error: EBUSY unlink'}) == {},
          'PostToolUseFailure fired on user interrupt')

    # 4. gate.js Code Mode chaining: 6 consecutive Read/Grep/Glob calls -> 1 line once; never blocks; silent in worker or after Edit
    tr_chain = d / 'chain.jsonl'
    rows = [{'type': 'user', 'message': {'content': 'find all endpoints'}}]
    for i in range(6):
        tool = ['Read', 'Grep', 'Glob'][i % 3]
        rows.append({'type': 'assistant', 'message': {'model': 'claude-sonnet-5-5', 'content': [{'type': 'tool_use', 'id': f'r{i}', 'name': tool, 'input': {'pattern': f'p{i}'}}]}})
        rows.append({'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': f'r{i}', 'content': f'hit {i}'}]}})
    tr_chain.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    ch = lambda **more: (hook('gate.js', {'hook_event_name': 'PreToolUse', 'tool_name': 'Read', 'tool_input': {'file_path': str(d / 'a.js')},
                                          'transcript_path': str(tr_chain), 'prompt_id': 'c1', **more}).get('hookSpecificOutput') or {})
    check(ch(agent_id='w1') == {}, 'chaining: fired inside a worker')
    first = ch()
    check('code mode' in first.get('additionalContext', '') and 'helena:scout' in first.get('additionalContext', '') and 'permissionDecision' not in first,
          f'chaining: no Code Mode nudge after 6 reads: {first!r}')
    check(ch() == {}, 'chaining: repeated in the same request')
    # An edit breaks the consecutive read streak
    rows.append({'type': 'assistant', 'message': {'model': 'claude-sonnet-5-5', 'content': [{'type': 'tool_use', 'id': 'e1', 'name': 'Edit', 'input': {'file_path': 'a.js'}}]}})
    rows.append({'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'e1', 'content': 'ok'}]}})
    tr_chain.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    check(ch(prompt_id='c2') == {}, 'chaining: fired right after an Edit broke the read streak')

for e in errors:
    print('failed:', e)
print(f'{len(errors)} error(s)' if errors else 'PASS  test_lifecycle')
sys.exit(1 if errors else 0)
