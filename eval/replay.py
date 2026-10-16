"""Replays real tool calls through gate.js of the working tree and of a git ref, and lists every decision that changed.
No LLM, no tool is ever executed: the hook only decides. Runs with a temp HOME so ~/.helena is never written.

    python eval/replay.py [--last 500] [--from ~/.claude/projects] [--ref main] [--json out.json]
"""
import argparse, concurrent.futures as cf, glob, io, json, os, pathlib, subprocess, sys, tarfile, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def events(src, last):
    """The last `last` tool_use blocks of the transcripts under src, newest transcripts last, as PreToolUse events."""
    out = []
    for f in sorted(glob.glob(os.path.join(src, '*', '*.jsonl')), key=os.path.getmtime):
        try:
            lines = open(f, encoding='utf-8', errors='replace').read().splitlines()
        except OSError:
            continue
        for line in lines:
            if '"tool_use"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            c = (d.get('message') or {}).get('content')
            if d.get('type') != 'assistant' or not isinstance(c, list):
                continue
            for b in c:
                if b.get('type') == 'tool_use':
                    out.append({'hook_event_name': 'PreToolUse', 'tool_name': b.get('name', ''), 'tool_input': b.get('input') or {},
                                'cwd': d.get('cwd') or '', 'session_id': d.get('sessionId') or ''})
    return out[-last:]


def run(hook, ev, env, cwd):
    try:
        r = subprocess.run(['node', str(hook)], input=json.dumps(ev), capture_output=True, text=True, encoding='utf-8',
                           env=env, cwd=cwd, timeout=20)
        if r.returncode:
            return 'crash', (r.stderr.strip().splitlines() or ['exit %d' % r.returncode])[-1]
        o = json.loads(r.stdout)['hookSpecificOutput'] if r.stdout.strip() else {}
        return o.get('permissionDecision', 'allow'), o.get('permissionDecisionReason', '')
    except subprocess.TimeoutExpired:
        return 'crash', 'timeout'
    except ValueError:
        return 'crash', 'bad output'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--last', type=int, default=500)
    ap.add_argument('--from', dest='src', default=os.path.expanduser('~/.claude/projects'))
    ap.add_argument('--ref', default='main')
    ap.add_argument('--json')
    a = ap.parse_args()
    evs = events(a.src, a.last)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        old = tmp / 'old'
        old.mkdir()
        git = subprocess.run(['git', '-C', str(ROOT), 'archive', a.ref, 'helena'], capture_output=True)
        if git.returncode:
            sys.exit('cannot extract helena/ at ' + a.ref + ': ' + git.stderr.decode().strip())
        tarfile.open(fileobj=io.BytesIO(git.stdout)).extractall(old, filter='data')
        home = tmp / 'home'
        home.mkdir()
        env = {k: v for k, v in os.environ.items() if k != 'HELENA_DISTILLING'}
        env.update(HOME=str(home), USERPROFILE=str(home), HELENA_VAULT=str(home / 'Helena'))
        hooks = {'new': ROOT / 'helena' / 'hooks' / 'gate.js', 'old': old / 'helena' / 'hooks' / 'gate.js'}
        with cf.ThreadPoolExecutor(8) as ex:
            futs = [{k: ex.submit(run, h, ev, env, str(tmp)) for k, h in hooks.items()} for ev in evs]
            res = [{k: f.result() for k, f in d.items()} for d in futs]
    counts = {k: {x: sum(r[k][0] == x for r in res) for x in ('allow', 'ask', 'deny', 'crash')} for k in hooks}
    changed = [{'tool': e['tool_name'], 'input': e['tool_input'], 'cwd': e['cwd'], 'old': r['old'][0], 'new': r['new'][0],
                'reason': r['new'][1] or r['old'][1]} for e, r in zip(evs, res) if r['old'][0] != r['new'][0]]
    print(f'events replayed: {len(evs)}   (working tree vs {a.ref})')
    for k, name in (('old', a.ref), ('new', 'working tree')):
        print(f'  {name:13} ' + '  '.join(f'{x} {n}' for x, n in counts[k].items()))
    print(f'changed decisions: {len(changed)}')
    for c in changed:
        i = c['input']
        what = str(i.get('command') or i.get('file_path') or i.get('path') or i.get('pattern') or '')[:100].replace('\n', ' ')
        print(f"  {c['tool']}: {what}  {c['old']} -> {c['new']}  {c['reason'][:80]}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({'ref': a.ref, 'events': len(evs), 'counts': counts, 'changed': changed}, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
