"""Hook speed. Every tool call waits for Helena's hooks, so a slow one taxes the whole session. Runs each command hook in
hooks.json with a harmless fake event (fresh git repo, fake HOME, HELENA_EVAL=1), 5 times, and compares the median with
a budget: 1500 ms per hook, 3000 ms for start.js; HELENA_SPEED_MS replaces the 1500 (start.js gets twice it). No LLM.

    python eval/test_speed.py
"""
import json, os, pathlib, re, statistics, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'helena'
BASE = float(os.environ.get('HELENA_SPEED_MS') or 1500)
RUNS = 5

# hooks that cannot run harmlessly with a fake event
SKIP = {
    'done.js': 'runs the project tests',
    'check.js': 'may open a browser / fetch pages',
    'end.js': 'exits at once under HELENA_EVAL (distills with a model otherwise)',
}


def event(name, matcher):
    tool = 'Agent' if matcher.startswith('Agent') else 'Bash'
    tin = {'prompt': 'ls', 'subagent_type': 'general-purpose'} if tool == 'Agent' else {'command': 'ls'}
    return {
        'SessionStart': {'source': 'startup'},
        'UserPromptSubmit': {'prompt': 'fix the typo in the readme'},
        'PreToolUse': {'tool_name': tool, 'tool_input': tin},
        'PostToolUse': {'tool_name': tool, 'tool_input': tin, 'tool_response': {'stdout': 'a.txt\n', 'stderr': '', 'interrupted': False}},
        'Stop': {},
        'SubagentStart': {'agent_type': 'general-purpose', 'agent_id': 'a1'},
        'SubagentStop': {'agent_id': 'a1', 'last_assistant_message': 'done: a.txt'},
        'PreCompact': {'trigger': 'auto'},
        'SessionEnd': {'reason': 'other'},
    }[name]


hooks = json.loads((ROOT / 'hooks' / 'hooks.json').read_text(encoding='utf-8'))['hooks']
slow, rows = [], []
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    home, d = tmp / 'home', tmp / 'app'
    (home / '.helena').mkdir(parents=True)
    d.mkdir()
    subprocess.run(['git', 'init', '-q'], cwd=d, check=True)
    env = {k: v for k, v in os.environ.items() if k != 'HELENA_DISTILLING'}
    env.update(USERPROFILE=str(home), HOME=str(home), HELENA_EVAL='1', HELENA_VAULT=str(home / 'vault'))
    seen = set()
    for ev_name, groups in hooks.items():
        for g in groups:
            for h in g['hooks']:
                if h.get('type') != 'command':
                    continue
                script = re.search(r'hooks/([\w.-]+\.js)', h['command']).group(1)
                if (script, ev_name) in seen:
                    continue
                seen.add((script, ev_name))
                if script in SKIP:
                    print(f'{script} {ev_name}  skipped: {SKIP[script]}')
                    continue
                payload = json.dumps({'cwd': str(d), 'session_id': 'speed1234', 'hook_event_name': ev_name,
                                      **event(ev_name, g.get('matcher', ''))})
                times = []
                for _ in range(RUNS):
                    t0 = time.perf_counter()
                    subprocess.run(['node', str(ROOT / 'hooks' / script)], input=payload, capture_output=True, text=True,
                                   encoding='utf-8', env=env, cwd=d, timeout=60)
                    times.append((time.perf_counter() - t0) * 1000)
                med = statistics.median(times)
                budget = BASE * 2 if script == 'start.js' else BASE
                print(f'{script} {ev_name}  median {med:.0f} ms')
                if med > budget:
                    slow.append(f'{script} {ev_name} ({med:.0f} ms > {budget:.0f} ms)')

if slow:
    print('slow:', '; '.join(slow))
    sys.exit(1)
print('ok')
