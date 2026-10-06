"""Where your tokens went: per day, per project, how much was re-read from cache, and what filled the context.

    python helena/budget.py [days]      # default 7; /helena:budget runs this

Reads the usage that Claude Code already writes in every transcript. No LLM call, costs nothing.
"""
import collections, json, pathlib, statistics, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from history import HOME, sessions  # noqa: E402


def k(n):
    return f'{n / 1e6:.1f}M' if n >= 1e6 else f'{n / 1e3:.0f}k' if n >= 1e3 else str(n)


def main():
    sys.stdout.reconfigure(encoding='utf-8')  # Windows console defaults to cp1252
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    per_day, per_project, tools_out = collections.Counter(), collections.Counter(), collections.Counter()
    biggest, first_ctx, per_msg, totals = [], [], [], collections.Counter()
    n_sessions = 0
    for s in sessions(days):
        if not s['usage']:
            continue
        n_sessions += 1
        project = pathlib.Path(s['cwd'] or '?').name
        first_ctx.append(s['usage'][0]['input'] + s['usage'][0]['write'] + s['usage'][0]['read'])
        per_msg.append(len(s['usage']))
        for u in s['usage']:
            total = u['input'] + u['write'] + u['read'] + u['output']
            per_day[u['ts'][:10]] += total
            per_project[project] += total
            for key in ('input', 'write', 'read', 'output'):
                totals[key] += u[key]
        names = {i: (n, inp) for i, n, inp in s['tools']}
        for tid, size in s['outputs']:
            name, inp = names.get(tid, ('?', {}))
            tools_out[name] += size
            biggest.append((size, name, str(inp.get('command') or inp.get('file_path') or '')[:70]))

    if not n_sessions:
        print(f'No sessions in the last {days} days.')
        return
    context = totals['input'] + totals['write'] + totals['read']
    print(f'Last {days} days: {n_sessions} sessions, {k(context + totals["output"])} tokens '
          f'({k(context)} context read in, {k(totals["output"])} written out)')
    print(f'Re-read from cache: {totals["read"] / max(context, 1):.0%} of the context '
          f'(cheaper than fresh input, but it still counts toward the plan limit)')
    print(f'Fixed context at session start (median): {k(statistics.median(first_ctx))} tokens, re-read on every message')
    msgs = sum(per_msg)
    print(f'Average context per message: {k(context // max(msgs, 1))} over {msgs} messages. '
          'Every message re-reads all of it, so long sessions cost the most; HANDOFF.md + /clear resets it.\n')
    print('Per day:')
    for day, n in sorted(per_day.items())[-days:]:
        print(f'  {day}  {k(n):>7}  ' + '█' * max(1, round(n / max(per_day.values()) * 30)))
    print('\nPer project:')
    for p, n in per_project.most_common(6):
        print(f'  {p[:28]:28} {k(n):>7}')
    print('\nWhat filled the context (tool output, characters):')
    for t, n in tools_out.most_common(6):
        print(f'  {t[:28]:28} {k(n):>7}')
    print('\nBiggest single outputs:')
    for size, name, what in sorted(biggest, reverse=True)[:5]:
        print(f'  {k(size):>6}  {name}: {what}')

    own = [json.loads(l) for l in open(HOME / 'ledger.jsonl', encoding='utf-8')] if (HOME / 'ledger.jsonl').exists() else []
    own = [e for e in own if e.get('ts', '') >= min(per_day)]
    if own:
        print(f"\nHelena's own background work: {len(own)} Haiku calls, "
              f"{k(sum(e.get('tokens', 0) for e in own))} tokens, ${sum(e.get('cost', 0) for e in own):.2f}")


if __name__ == '__main__':
    main()
