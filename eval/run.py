"""Helena's benchmark: runs each task with and without the plugin and compares the pass rate.

    python eval/run.py                         # every task, 1 round
    python eval/run.py git-rule -n 3           # one task, 3 rounds per column
    python eval/run.py --model opus            # another model (default: sonnet, to save quota)

Each round happens in a clean copy of the fixture, in a temp folder outside the repo.
A skill only joins Helena if the "helena" column beats "base".

Tasks come from eval/tasks/ (ship with Helena) and ~/.helena/eval/tasks/ (yours: they depend on your memory and kits).
A task folder: prompt.md, fixture/, check.py (exit 0 = pass; last printed line shows up in the table), and optionally
setup.py (prepares the folder before the session), prepare.py (runs alongside the session) and ab.json (what differs
between the columns; {helena} and {task} become paths). Fake CLIs for tasks go in eval/shims/ or ~/.helena/eval/shims/.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys, tempfile

# built at runtime so no key-shaped string lives in the repo (secret scanners and the guard hook)
FAKE_KEY = 'sk_' + 'live_' + '51FakeX9' + 'X9' * 12

ROOT = pathlib.Path(__file__).resolve().parent
HELENA = ROOT.parent / 'helena'
MINE = pathlib.Path.home() / '.helena' / 'eval'
CLAUDE = shutil.which('claude') or 'claude'


def run(task, with_helena, model):
    folder = pathlib.Path(tempfile.mkdtemp(prefix=f'helena-{task.name}-'))
    shutil.copytree(task / 'fixture', folder, dirs_exist_ok=True)
    shims = os.pathsep.join(str(d / 'shims') for d in (ROOT, MINE) if (d / 'shims').exists())
    env = dict(os.environ, HELENA_EVAL='1', HELENA_LOG=str(folder / '.shim.log'), PATH=shims + os.pathsep + os.environ['PATH'])
    # prompt goes through stdin: on Windows claude.CMD passes through cmd.exe, which cuts arguments at line breaks
    cmd = [CLAUDE, '-p', '--output-format', 'json', '--no-session-persistence', '--dangerously-skip-permissions', '--model', model]
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
    return chk.returncode == 0, result.get('total_cost_usd') or 0, folder, note


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
    for t in chosen:
        for with_helena in (False, True):
            for _ in range(a.n):
                ok, cost, folder, note = run(t, with_helena, a.model)
                score[with_helena][0] += ok
                score[with_helena][1] += 1
                print(f"{t.name:24} {'helena' if with_helena else 'base':7} {'PASS' if ok else 'fail':5} "
                      f"${cost:.3f}  {note}  {folder}", flush=True)
    for with_helena, (ok, total) in score.items():
        print(f"{'helena' if with_helena else 'base':7} {ok}/{total}")


if __name__ == '__main__':
    main()
