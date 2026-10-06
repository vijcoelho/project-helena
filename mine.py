"""Observe: reads your Claude Code history and shows what you repeat and what you correct.

    python mine.py            # summary in the terminal + data/messages.jsonl (secrets masked)

Skill candidates come from here: a pattern that repeats becomes a task in eval/,
and only becomes a skill in helena/ if the benchmark proves it helps.
"""
import glob, json, os, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / 'helena'))
from distill import SECRET  # noqa: E402

HISTORY = os.path.expanduser('~/.claude/projects')
OUT = pathlib.Path(__file__).parent / 'data'

# Machine-written messages (subagent prompts, other tools' evals) are not your workflow.
ROBOT = re.compile(r'^(<|\[|Another Claude|This session|You are|Worktree:|Voc[eê] [eé] um)', re.I)

# Themes in English and Portuguese; add your own words here.
THEMES = {
    'run locally / stop': r'\b(run|start|restart|localhost|roda|rodar|reinicia)\b',
    'commit / push / merge': r'\b(commit|comita|push|merge|branch)',
    'resume / handoff': r'(continue|pick up|where (we|you) left|handoff|continua|onde (a gente )?parou|salva tudo)',
    'deploy / docker': r'(docker|deploy|vps|coolify|vercel|kubernetes)',
    'visual / design': r'(visual|design|minimal|animat|anima|background|fundo|navbar|colou?r|cor(es)?\b|font)',
    'readability': r'(hard to read|can.?t read|unreadable|contrast|dif[ií]cil de ler|n[aã]o (consigo|da para) ler)',
    'images': r'(image|imagem|imagens|picture|photo)',
    'video / motion': r'(video|v[ií]deo|motion|render)',
    'tests / security': r'(test|teste|testa|security|seguran|bug|audit|valid)',
    'research / plan': r'(research|pesquisa|plan\b|plano|architect|arquiteta|what.?s left|o que falta)',
}
# A correction: you told the AI it got something wrong. These are the best memory candidates.
CORRECTION = re.compile(r"^(no[,.! ]|n[aã]o[,.! ]|nope|actually|na verdade|stop |para de |don.?t |never |nunca |wrong|errado)", re.I)


def messages():
    for f in glob.glob(HISTORY + '/**/*.jsonl', recursive=True):
        project = pathlib.Path(f).relative_to(HISTORY).parts[0]
        for line in open(f, encoding='utf-8', errors='ignore'):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            c = (d.get('message') or {}).get('content')
            if d.get('type') == 'user' and isinstance(c, str) and len(c) > 15 and not ROBOT.search(c.strip()):
                yield project, d.get('timestamp', ''), SECRET.sub('***', c.strip())


def main():
    msgs = list(messages())
    OUT.mkdir(exist_ok=True)
    with open(OUT / 'messages.jsonl', 'w', encoding='utf-8') as f:
        for p, ts, c in msgs:
            f.write(json.dumps({'project': p, 'ts': ts, 'text': c}, ensure_ascii=False) + '\n')

    print(f'{len(msgs)} messages of yours in {len({m[0] for m in msgs})} projects\n')
    for name, rx in sorted(THEMES.items(), key=lambda kv: -sum(bool(re.search(kv[1], m[2], re.I)) for m in msgs)):
        print(f'{sum(bool(re.search(rx, m[2], re.I)) for m in msgs):4}  {name}')
    corrections = [m for m in msgs if CORRECTION.search(m[2])]
    print(f'\n{len(corrections)} corrections (most recent first):')
    for p, ts, c in sorted(corrections, key=lambda m: m[1], reverse=True)[:15]:
        print(f'  - {c[:110]}')


if __name__ == '__main__':
    main()
