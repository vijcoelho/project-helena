"""Helena's benchmark: runs each task with and without the plugin and compares the pass rate.

    python eval/run.py                         # every task, 1 round
    python eval/run.py git-rule -n 3           # one task, 3 rounds per column
    python eval/run.py --model opus            # another model (default: sonnet, to save quota)

Each round happens in a clean copy of the fixture, in a temp folder outside the repo.
A skill only joins Helena if the "helena" column beats "base".
Each run also records its tokens and cost; the per-task result (pass rate, tokens, lift) is saved in eval/results.json,
which eval/registry.py turns into the public registry. A task's `uses` file names what it measures (e.g. `skill:handoff`).

Tasks come from eval/tasks/ (ship with Helena) and ~/.helena/eval/tasks/ (yours: they depend on your memory and kits).
A task folder: prompt.md, fixture/, check.py (exit 0 = pass; last printed line shows up in the table), and optionally
setup.py (prepares the folder before the session), prepare.py (runs alongside the session), ab.json (what differs
between the columns; {helena} and {task} become paths) and an empty `persist` file (the session keeps its transcript,
which the done check reads). Fake CLIs for tasks go in eval/shims/ or ~/.helena/eval/shims/.
"""
import argparse, datetime, json, os, pathlib, shutil, subprocess, sys, tempfile

# built at runtime so no key-shaped string lives in the repo (secret scanners and the guard hook)
FAKE_KEY = 'sk_' + 'live_' + '51FakeX9' + 'X9' * 12

ROOT = pathlib.Path(__file__).resolve().parent
HELENA = ROOT.parent / 'helena'
MINE = pathlib.Path.home() / '.helena' / 'eval'
RESULTS = ROOT / 'results.json'
CLAUDE = shutil.which('claude') or 'claude'


def run(task, with_helena, model):
    folder = pathlib.Path(tempfile.mkdtemp(prefix=f'helena-{task.name}-'))
    shutil.copytree(task / 'fixture', folder, dirs_exist_ok=True)
    shims = os.pathsep.join(str(d / 'shims') for d in (ROOT, MINE) if (d / 'shims').exists())
    env = dict(os.environ, HELENA_EVAL='1', HELENA_LOG=str(folder / '.shim.log'), PATH=shims + os.pathsep + os.environ['PATH'])
    # prompt goes through stdin: on Windows claude.CMD passes through cmd.exe, which cuts arguments at line breaks
    cmd = [CLAUDE, '-p', '--output-format', 'json', '--dangerously-skip-permissions', '--model', model]
    # a hook that reads the transcript (done.js) sees nothing without one: a task with a `persist` file keeps its session on disk
    if not (task / 'persist').exists():
        cmd.append('--no-session-persistence')
    ab = json.loads((task / 'ab.json').read_text()) if (task / 'ab.json').exists() else \
        {'base': [], 'helena': ['--plugin-dir', '{helena}']}
    cmd += [x.replace('{helena}', str(HELENA)).replace('{task}', str(task)) for x in ab['helena' if with_helena else 'base']]
    # an installed Helena would leak into the base column: turn it off in both (the helena column uses the repo's)
    cmd += ['--settings', str(ROOT / 'no-helena.json')]
    if (task / 'setup.py').exists():
        subprocess.run([sys.executable, str(task / 'setup.py'), str(folder)], check=True)
    prep = (subprocess.Popen([sys.executable, str(task / 'prepare.py'), str(folder)])
            if (task / 'prepare.py').exists() else None)
    try:
        r = subprocess.run(cmd, input=(task / 'prompt.md').read_text(encoding='utf-8').replace('{FAKE_KEY}', FAKE_KEY),
                           cwd=folder, env=env, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=900)
        result = json.loads(r.stdout or '{}')
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        result = {}
    (folder / '.result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    chk = subprocess.run([sys.executable, str(task / 'check.py'), str(folder)], capture_output=True,
                         text=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    if prep:
        prep.kill()
        kill_ports(folder)
    note = (chk.stdout.strip().splitlines() or [''])[-1][:90]
    u = result.get('usage') or {}
    tokens = sum(u.get(k) or 0 for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'))
    return chk.returncode == 0, result.get('total_cost_usd') or 0, folder, note, tokens


def kill_ports(folder):
    """Stops only the servers the agent started (ports where prepare.py saw the fixture's app)."""
    seen = folder / '.ports_seen'
    if not seen.exists():
        return
    netstat = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
    for port in set(seen.read_text().split()):
        for line in netstat.splitlines():
            parts = line.split()
            if 'LISTENING' in parts and parts[1].endswith(f':{port}'):
                subprocess.run(['taskkill', '/PID', parts[-1], '/T', '/F'], capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tasks', nargs='*')
    ap.add_argument('-n', type=int, default=1)
    ap.add_argument('--model', default='sonnet')
    a = ap.parse_args()

    found = sorted((p for d in (ROOT / 'tasks', MINE / 'tasks') if d.exists() for p in d.iterdir() if p.is_dir()),
                   key=lambda p: p.name)
    chosen = [t for t in found if not a.tasks or t.name in a.tasks]
    score = {False: [0, 0], True: [0, 0]}
    saved = json.loads(RESULTS.read_text(encoding='utf-8')) if RESULTS.exists() else {}
    for t in chosen:
        col = {}
        for with_helena in (False, True):
            runs = [run(t, with_helena, a.model) for _ in range(a.n)]
            for ok, cost, folder, note, tokens in runs:
                print(f"{t.name:24} {'helena' if with_helena else 'base':7} {'PASS' if ok else 'fail':5} "
                      f"${cost:.3f} {tokens // 1000:>4}k tok  {note}  {folder}", flush=True)
            score[with_helena][0] += sum(r[0] for r in runs)
            score[with_helena][1] += len(runs)
            col['helena' if with_helena else 'base'] = {'pass': sum(r[0] for r in runs), 'runs': len(runs),
                                                        'cost': round(sum(r[1] for r in runs) / len(runs), 4),
                                                        'tokens': sum(r[4] for r in runs) // len(runs)}
        b, h = col['base'], col['helena']
        print(f"{t.name:24} lift {h['pass'] / h['runs'] - b['pass'] / b['runs']:+.0%}, "
              f"tokens {h['tokens'] - b['tokens']:+,} per run", flush=True)
        if t.parent == ROOT / 'tasks':  # your own tasks (~/.helena/eval) stay out of the shared results file
            uses = (t / 'uses').read_text().strip() if (t / 'uses').exists() else ''
            saved[t.name] = {'uses': uses, 'model': a.model, 'date': datetime.date.today().isoformat(), **col}
    if saved:
        RESULTS.write_text(json.dumps(saved, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    for with_helena, (ok, total) in score.items():
        print(f"{'helena' if with_helena else 'base':7} {ok}/{total}")


if __name__ == '__main__':
    main()
