"""The registry: every piece of Helena with what it costs in context, what the security scan says and what the benchmark
measured. A piece without a benchmark says so instead of claiming a win.

    python eval/registry.py          # writes site/registry.json (the site's registry section reads it)

Cost in context: a hook runs outside the model, so it costs nothing until it speaks; a skill costs its description in
every session (always) and its full text only when a request loads it (on use).
Lift: pass rate with Helena minus without, over every benchmark task whose `uses` file names the piece (eval/results.json).
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'helena'))
from scan import scan, verdict  # noqa: E402

tokens = lambda text: round(len(text) / 4)


def pieces():
    for f in sorted((ROOT / 'helena' / 'hooks').glob('*.js')):
        hooked = re.search(rf'hooks/{f.name}', (ROOT / 'helena' / 'hooks' / 'hooks.json').read_text())
        if hooked:
            yield {'name': f.stem, 'kind': 'hook', 'always': 0, 'on_use': 0, 'scan': 'n/a'}
    for md in sorted((ROOT / 'helena' / 'skills').glob('*/SKILL.md')):
        text = md.read_text(encoding='utf-8')
        desc = (re.search(r'^description:\s*(.+)$', text, re.M) or [None, ''])[1]
        yield {'name': md.parent.name, 'kind': 'skill', 'always': tokens(desc), 'on_use': tokens(text), 'scan': verdict(scan(md.parent))}


def main():
    results = json.loads((ROOT / 'eval' / 'results.json').read_text(encoding='utf-8')) if (ROOT / 'eval' / 'results.json').exists() else {}
    out = []
    for p in pieces():
        tasks = {t: r for t, r in results.items() if r.get('uses') == f"{p['kind']}:{p['name']}"}
        if tasks:
            col = lambda c, k: sum(r[c][k] for r in tasks.values())
            p.update(tasks=sorted(tasks), runs=col('helena', 'runs'), base=col('base', 'pass'), helena=col('helena', 'pass'),
                     lift=round(col('helena', 'pass') / col('helena', 'runs') - col('base', 'pass') / col('base', 'runs'), 2),
                     model=sorted({r['model'] for r in tasks.values()}), date=max(r['date'] for r in tasks.values()))
        out.append(p)
    f = ROOT / 'site' / 'registry.json'
    f.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    for p in out:
        lift = f"{p['helena']}/{p['runs']} vs {p['base']}/{p['runs']} ({p['lift']:+.0%})" if 'lift' in p else 'not benchmarked yet'
        print(f"{p['kind']:5} {p['name']:12} context {p['always']:>4} always / {p['on_use']:>5} on use  scan {p['scan']:8} {lift}")
    print(f'{len(out)} pieces -> {f}')


if __name__ == '__main__':
    main()
