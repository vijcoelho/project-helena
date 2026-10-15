"""Helena's benchmark: runs each task with and without the plugin and compares the pass rate.

    python eval/run.py                         # every task, 1 round
    python eval/run.py git-rule -n 3           # one task, 3 rounds per column
    python eval/run.py --model opus            # another model (default: sonnet, to save quota)
    python eval/run.py -n 3 --model haiku --out eval/frontier/haiku.json   # one file per model, for extras/chart.py
    python eval/run.py --probe                 # Helena's fixed weight: one "Reply OK" call per column, no task

With -n above 1 the columns take turns (base, helena, then helena, base...), so neither always runs on a warm cache.
Each column records its turns and its tokens split four ways (uncached, cache write, cache read, output): a saving that
comes with more turns shows up there, not only in the total.

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
    used = result.get('modelUsage') or {}  # the alias (--model sonnet) says nothing a year later: keep the id that answered
    return {'ok': chk.returncode == 0, 'cost': result.get('total_cost_usd') or 0, 'folder': folder, 'note': note,
            'turns': result.get('num_turns') or 0, 'parts': parts(result),
            'model_id': max(used, key=lambda m: used[m].get('costUSD') or 0, default='')}


PARTS = {'uncached': 'input_tokens', 'cache_write': 'cache_creation_input_tokens',
         'cache_read': 'cache_read_input_tokens', 'output': 'output_tokens'}


def parts(result):
    u = result.get('usage') or {}
    return {k: u.get(v) or 0 for k, v in PARTS.items()}


def probe(model):
    """What Helena adds before any work: one "Reply OK" call in an empty folder, per column (a few cents)."""
    for with_helena in (False, True):
        folder = tempfile.mkdtemp(prefix='helena-probe-')
        cmd = [CLAUDE, '-p', '--output-format', 'json', '--max-turns', '1', '--no-session-persistence',
               '--model', model, '--settings', str(ROOT / 'no-helena.json')]
        cmd += ['--plugin-dir', str(HELENA)] if with_helena else []
        r = subprocess.run(cmd, input='Reply OK', cwd=folder, env=dict(os.environ, HELENA_EVAL='1'), capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=300)
        try:
            p = parts(json.loads(r.stdout or '{}'))
        except json.JSONDecodeError:
            p = {}
        print(f"{'helena' if with_helena else 'base':7} {sum(p.values()):>7,} tok  " +
              '  '.join(f'{k} {v:,}' for k, v in p.items()), flush=True)


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
    ap.add_argument('--out', type=pathlib.Path, default=RESULTS)
    ap.add_argument('--probe', action='store_true')
    a = ap.parse_args()
    if a.probe:
        return probe(a.model)

    found = sorted((p for d in (ROOT / 'tasks', MINE / 'tasks') if d.exists() for p in d.iterdir() if p.is_dir()),
                   key=lambda p: p.name)
    chosen = [t for t in found if not a.tasks or t.name in a.tasks]
    score = {False: [0, 0], True: [0, 0]}
    saved = json.loads(a.out.read_text(encoding='utf-8')) if a.out.exists() else {}
    for t in chosen:
        runs = {False: [], True: []}
        for i in range(a.n):
            for with_helena in ((False, True) if i % 2 == 0 else (True, False)):
                r = run(t, with_helena, a.model)
                runs[with_helena].append(r)
                print(f"{t.name:24} {'helena' if with_helena else 'base':7} {'PASS' if r['ok'] else 'fail':5} "
                      f"${r['cost']:.3f} {sum(r['parts'].values()) // 1000:>4}k tok {r['turns']:>3} turns  "
                      f"{r['note']}  {r['folder']}", flush=True)
        col = {}
        for with_helena, rs in runs.items():
            score[with_helena][0] += sum(r['ok'] for r in rs)
            score[with_helena][1] += len(rs)
            n, ok, cost = len(rs), sum(r['ok'] for r in rs), sum(r['cost'] for r in rs)
            avg = {k: sum(r['parts'][k] for r in rs) // n for k in PARTS}
            # a cheap run that fails is not a saving: what counts is what one solved task cost
            col['helena' if with_helena else 'base'] = {
                'pass': ok, 'runs': n, 'cost': round(cost / n, 4), 'solved_cost': round(cost / ok, 4) if ok else None,
                'tokens': sum(avg.values()), 'parts': avg, 'turns': round(sum(r['turns'] for r in rs) / n, 1),
                'model_id': rs[0]['model_id']}
        b, h = col['base'], col['helena']
        solved = lambda c: f"${c['solved_cost']:.3f}" if c['pass'] else 'none solved'
        print(f"{t.name:24} lift {h['pass'] / h['runs'] - b['pass'] / b['runs']:+.0%}, "
              f"tokens {h['tokens'] - b['tokens']:+,} per run, turns {b['turns']} -> {h['turns']}, "
              f"per solved task: base {solved(b)}, helena {solved(h)}", flush=True)
        if t.parent == ROOT / 'tasks':  # your own tasks (~/.helena/eval) stay out of the shared results file
            uses = (t / 'uses').read_text().strip() if (t / 'uses').exists() else ''
            saved[t.name] = {'uses': uses, 'model': a.model, 'date': datetime.date.today().isoformat(), **col}
            a.out.parent.mkdir(parents=True, exist_ok=True)  # written per task: a long run that dies keeps what it finished
            a.out.write_text(json.dumps(saved, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    for with_helena, (ok, total) in score.items():
        print(f"{'helena' if with_helena else 'base':7} {ok}/{total}")


if __name__ == '__main__':
    main()
