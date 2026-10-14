"""The delegate hook: a built-in worker started without a model is pinned below the main one, always; with .helena/delegate,
only so many run at once and only so many start per request. A worker's own edits get the done check.
No LLM: python eval/test_delegate.py
"""
import json, os, pathlib, subprocess, sys, tempfile

HOOKS = pathlib.Path(__file__).resolve().parent.parent / 'helena' / 'hooks'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)


with tempfile.TemporaryDirectory() as tmp:
    d, home = pathlib.Path(tmp) / 'app', pathlib.Path(tmp) / 'home'
    (d / '.helena').mkdir(parents=True)
    home.mkdir()
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home), HELENA_EVAL='1')
    n = 0

    def hook(name, ev):
        r = subprocess.run(['node', str(HOOKS / name)], input=json.dumps({'cwd': str(d), **ev}),
                           capture_output=True, text=True, encoding='utf-8', env=env, timeout=30)
        return json.loads(r.stdout) if r.stdout.strip() else {}

    def agent(session='s', transcript_path='', **inp):
        global n, last
        n += 1
        out = hook('delegate.js', {'hook_event_name': 'PreToolUse', 'tool_name': 'Agent', 'session_id': session, 'tool_use_id': f't{n}',
                                   'transcript_path': transcript_path,
                                   'tool_input': {'description': 'find it', 'prompt': 'where is add()', **inp}}).get('hookSpecificOutput', {})
        last = out.get('updatedInput') or {}
        return out.get('permissionDecision', ''), last.get('model', ''), out.get('permissionDecisionReason', '')

    stop = lambda session='s': hook('delegate.js', {'hook_event_name': 'SubagentStop', 'session_id': session})
    said = lambda session='s': hook('router.js', {'prompt': 'now the next part', 'session_id': session})

    # ---- no file: the pins act (never above the main model), nothing is counted or capped
    def talking(model):  # a session whose last call was answered by `model`
        f = pathlib.Path(tmp) / f'{model}.jsonl'
        f.write_text(json.dumps({'type': 'assistant', 'timestamp': '2026-10-13T10:00:00Z', 'message': {
            'model': f'claude-{model}-5-5', 'content': [], 'usage': {'input_tokens': 9, 'cache_read_input_tokens': 90000}}}) + '\n')
        return {'transcript_path': str(f)}

    got = [agent(subagent_type='Explore') for _ in range(10)]
    check(all(g == ('', 'haiku', '') for g in got), f'no file: Explore not pinned, or capped: {got}')
    check(not (home / '.helena' / 'warnings' / 's-workers').exists(), 'counted workers without .helena/delegate')
    check(agent(subagent_type='general-purpose', **talking('opus'))[1] == 'sonnet', 'Opus session: general-purpose not pinned to sonnet')
    check(agent(subagent_type='general-purpose', **talking('sonnet'))[1] == '', 'Sonnet session: a pin to sonnet saves nothing')
    check(agent(subagent_type='Explore', **talking('sonnet'))[1] == 'haiku', 'Sonnet session: Explore not pinned to haiku')
    check(agent(subagent_type='Explore', **talking('haiku'))[1] == '', 'Haiku session: a worker was moved up')

    # ---- pins: only built-ins that would run on the main model, and only when the call names no model
    (d / '.helena' / 'delegate').write_text('parallel: 2\nworkers: 4  # per request\n')
    check(agent(subagent_type='Explore')[1] == 'haiku', 'Explore not pinned to haiku')
    stop()
    check(agent(subagent_type='general-purpose')[1] == 'sonnet', 'general-purpose not pinned to sonnet')
    stop()
    check(agent(subagent_type='general-purpose', model='opus')[:2] == ('', ''), 'a call that names its model was repinned')
    stop()
    check(agent(subagent_type='helena:builder')[:2] == ('', ''), "an agent type with its own model was repinned")
    stop()

    # ---- workers per request: 4 started, the 5th is refused until the user speaks again
    decision, _, why = agent(subagent_type='Explore')
    check(decision == 'deny' and 'workers: 4' in why, f'5th worker of one request not refused: {decision} {why}')
    said()
    check(agent(subagent_type='Explore')[0] == '', 'a new request did not reset the count')

    # ---- at the same time: 2 running, the 3rd waits; a refused one takes no place
    check(agent(subagent_type='Explore')[0] == '', '2nd running worker refused')
    decision, _, why = agent(subagent_type='Explore')
    check(decision == 'deny' and 'at a time' in why, f'3rd running worker not refused: {decision} {why}')
    stop()
    check(agent(subagent_type='Explore')[0] == '', 'a finished worker did not free its place')

    # ---- settings: `off` turns a line off, another session starts clean
    (d / '.helena' / 'delegate').write_text('model: off\nsearch: sonnet\nparallel: off\nworkers: off\n')
    got = [agent('other', subagent_type='general-purpose') for _ in range(6)]
    check(all(g == ('', '', '') for g in got), f'`off` lines still acted: {got}')
    check(agent('other', subagent_type='Explore')[1] == 'sonnet', '`search:` not read')

    rows = [json.loads(l) for l in (home / '.helena' / 'audit.jsonl').read_text(encoding='utf-8').splitlines()]
    check(len(rows) == 2 and all(r['hook'] == 'delegate' and r['decision'] == 'deny' for r in rows), f'audit rows: {rows}')

    # ---- effort: only when the file asks, only on a pinned worker, never over an effort the call names
    check('effort' not in last, f'effort set without the line: {last}')
    (d / '.helena' / 'delegate').write_text('effort: medium\nparallel: off\nworkers: off\n')
    agent('other', subagent_type='Explore')
    check(last.get('effort') == 'medium' and last.get('model') == 'haiku', f'`effort:` not applied: {last}')
    agent('other', subagent_type='Explore', effort='low')
    check(last.get('effort') == 'low', f'an effort the call named was replaced: {last}')

    # ---- done check on a worker: its edits are in its own transcript
    (d / '.helena' / 'test').write_text('node -e "process.exit(1)"\n')
    sub = pathlib.Path(tmp) / 'agent-1.jsonl'
    sub.write_text('\n'.join(json.dumps(x) for x in [
        {'type': 'user', 'message': {'content': 'make total() handle empty arrays'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Edit', 'input': {'file_path': str(d / 'cart.js')}}]}},
    ]) + '\n')
    main = pathlib.Path(tmp) / 'main.jsonl'
    main.write_text(json.dumps({'type': 'user', 'message': {'content': 'do it'}}) + '\n')
    out = hook('done.js', {'hook_event_name': 'SubagentStop', 'session_id': 's', 'transcript_path': str(main), 'agent_transcript_path': str(sub)})
    check(out.get('decision') == 'block' and 'cart.js' in out.get('reason', ''), f"a worker's failing tests did not send it back: {out}")
    check(not hook('done.js', {'hook_event_name': 'Stop', 'session_id': 's', 'transcript_path': str(main)}), 'main thread blocked with no edits')

for e in errors:
    print('failed:', e)
print('ok: model pins by default and never upward, effort, workers per request and at a time, audit, done check on a worker' if not errors else f'{len(errors)} error(s)')
sys.exit(1 if errors else 0)
