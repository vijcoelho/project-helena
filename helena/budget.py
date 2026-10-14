"""Where your tokens went: per day, per project, what filled the context, files read twice, and every time the context
was paid in full instead of read from the cache (a pause past its lifetime, a model switch, a compaction).

    python helena/budget.py [days]      # default 7; /helena:budget runs this

Reads the usage that Claude Code already writes in every transcript. No LLM call, costs nothing.
"""
import collections, datetime, json, pathlib, statistics, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from history import HOME, sessions, subagents  # noqa: E402


def k(n):
    return f'{n / 1e6:.1f}M' if n >= 1e6 else f'{n / 1e3:.0f}k' if n >= 1e3 else str(n)


CAUSES = {  # why a call paid for the context in full instead of reading it from the cache, and what avoids it
    'pause': ('pause longer than the cache', 'answer before `cache until` in the status line, or /clear first'),
    'model': ('model switched mid-session', 'each model has its own cache: switch when a session starts'),
    'compact': ('context compacted', 'HANDOFF.md + /clear costs less than a summary of everything'),
    'other': ('other', ''),
}


def when(ts):
    try:
        return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0


def cache_breaks(usage):
    """Calls that did not find the previous call's context in the cache: [(cause, tokens paid in full)]."""
    out, ttl, prev = [], 300, None
    for u in usage:
        ctx = u['input'] + u['write'] + u['read']
        if not ctx:
            continue
        if prev and prev['ctx'] >= 20e3 and u['read'] < prev['ctx'] / 2:
            gap = when(u['ts']) - when(prev['ts']) if u['ts'] and prev['ts'] else 0
            cause = ('model' if u['model'] != prev['model'] else 'pause' if gap > ttl
                     else 'compact' if ctx < prev['ctx'] / 2 else 'other')
            out.append((cause, u['input'] + u['write']))
        ttl = u.get('ttl') or ttl
        prev = {**u, 'ctx': ctx}
    return out


def rereads(tools, sizes):
    """Reads of a file (same part of it) that was already read in the session and not edited since: {file: [characters]}."""
    seen, again = set(), collections.defaultdict(list)
    for tid, name, inp in tools:
        f = inp.get('file_path')
        if name == 'Read' and f:
            key = (f, inp.get('offset'), inp.get('limit'))
            if key in seen:
                again[f].append(sizes.get(tid, 0))
            seen.add(key)
        elif f:  # an edit: the next read of it is not a repeat
            seen = {k for k in seen if k[0] != f}
    return again


def main():
    sys.stdout.reconfigure(encoding='utf-8')  # Windows console defaults to cp1252
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    per_day, per_project, tools_out = collections.Counter(), collections.Counter(), collections.Counter()
    biggest, first_ctx, per_msg, totals = [], [], [], collections.Counter()
    breaks, cold, again = collections.defaultdict(lambda: [0, 0]), [], collections.defaultdict(list)
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
        for cause, paid in cache_breaks(s['usage']):
            breaks[cause][0] += 1
            breaks[cause][1] += paid
        later = s['usage'][1:]  # the first call of a session has nothing to read from
        if len(later) >= 5:
            cold.append((sum(u['read'] for u in later) / max(sum(u['input'] + u['write'] + u['read'] for u in later), 1), project))
        for f, chars in rereads(s['tools'], dict(s['outputs'])).items():
            again[f] += chars

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
    if again:
        print(f'\nSame file read again with no edit in between: {sum(map(len, again.values()))} times, '
              f'{k(sum(map(sum, again.values())))} characters that were already in the context')
        for f, chars in sorted(again.items(), key=lambda x: -sum(x[1]))[:3]:
            print(f'  {k(sum(chars)):>6}  {len(chars)}x  {f[-70:]}')

    print(f'\nCache: the context was paid in full again {sum(n for n, _ in breaks.values())} times, '
          f'{k(sum(t for _, t in breaks.values()))} tokens (a call that reads it from the cache pays a fraction)')
    for cause, (n, paid) in sorted(breaks.items(), key=lambda x: -x[1][1]):
        print(f'  {CAUSES[cause][0]:28} {n:>4} {k(paid):>7}  {CAUSES[cause][1]}')
    low = sorted(c for c in cold if c[0] < 0.85)
    if low:
        print(f'  Sessions under 85% read from the cache: {len(low)} of {len(cold)} '
              f"(lowest: {', '.join(f'{p} {r:.0%}' for r, p in low[:3])})")

    # subagents: their transcripts sit next to the parent session, outside the totals above
    groups, workers, starts = collections.defaultdict(collections.Counter), [], []
    for s in subagents(days):
        if not s['usage']:
            continue
        ctx = [u['input'] + u['write'] + u['read'] for u in s['usage']]
        starts.append((ctx[0], s['usage'][0]['write']))
        total = sum(ctx) + sum(u['output'] for u in s['usage'])
        who = (s['usage'][0]['model'].replace('claude-', ''), s['meta'].get('effort', '-'))
        groups[who].update(workers=1, calls=len(ctx), tokens=total, big=sum(c > 100e3 for c in ctx))
        workers.append((total, who, len(ctx), f"{s['meta'].get('agentType', '?')}: {s['meta'].get('description', '')}"[:60]))
    if workers:
        print(f'\nSubagents (not counted above; /usage does not show their cache reads): {len(workers)} workers, '
              f'{k(sum(w[0] for w in workers))} tokens')
        print(f"  {'model':18} {'effort':7} {'workers':>7} {'calls':>6} {'tokens':>7}  calls over 100k of context")
        for (model, effort), g in sorted(groups.items(), key=lambda x: -x[1]['tokens']):
            print(f"  {model[:18]:18} {effort:7} {g['workers']:>7} {g['calls']:>6} {k(g['tokens']):>7}  {g['big']}")
        # what a worker costs before it does anything: below this, doing the work in the session is cheaper
        print(f'  A worker starts at {k(statistics.median(c for c, _ in starts))} of context (median), '
              f'{k(statistics.median(w for _, w in starts))} of it written to the cache on that first call, not read from it')
        print('  Heaviest:')
        for total, (model, effort), calls, what in sorted(workers, reverse=True)[:5]:
            print(f'  {k(total):>6}  {model} {effort}, {calls} calls  {what}')

    own = [json.loads(l) for l in open(HOME / 'ledger.jsonl', encoding='utf-8')] if (HOME / 'ledger.jsonl').exists() else []
    own = [e for e in own if e.get('ts', '') >= min(per_day)]
    if own:
        print(f"\nHelena's own background work: {len(own)} Haiku calls, "
              f"{k(sum(e.get('tokens', 0) for e in own))} tokens, ${sum(e.get('cost', 0) for e in own):.2f}")


if __name__ == '__main__':
    main()
