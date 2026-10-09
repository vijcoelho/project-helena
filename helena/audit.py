"""What Helena's hooks blocked or asked about: secrets, made-up packages, destructive commands, weakened tests, team policy,
failed done checks. Every hook decision is one line in ~/.helena/audit.jsonl.

    python helena/audit.py [days]          # default 7; /helena:audit runs this
    python helena/audit.py 30 --json       # raw lines, for a team's own log tools
"""
import collections, datetime, json, pathlib, sys

LOG = pathlib.Path.home() / '.helena' / 'audit.jsonl'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    days = int(args[0]) if args else 7
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat(timespec='seconds')
    rows = []
    for line in LOG.open(encoding='utf-8') if LOG.exists() else []:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get('ts', '') >= since:
            rows.append(r)
    if '--json' in sys.argv:
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        return
    if not rows:
        print(f'Nothing blocked or asked about in the last {days} days.')
        return
    kind = collections.Counter(r['why'].split(':')[0].replace('Helena / ', '') for r in rows)
    print(f'Last {days} days: {len(rows)} decisions ({sum(r["decision"] == "deny" for r in rows)} denied, '
          f'{sum(r["decision"] == "ask" for r in rows)} asked, {sum(r["decision"] == "block" for r in rows)} sent back)')
    for k, n in kind.most_common():
        print(f'  {k:16} {n}')
    print('\nPer project:')
    for p, n in collections.Counter(r['project'] for r in rows).most_common(6):
        print(f'  {p[:28]:28} {n}')
    print('\nLatest:')
    for r in rows[-8:]:
        print(f"  {r['ts'][5:16].replace('T', ' ')}  {r['decision']:5} {r['what'][:60]}")


if __name__ == '__main__':
    main()
