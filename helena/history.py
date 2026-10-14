"""Reads Claude Code transcripts (~/.claude/projects/**/*.jsonl) into plain session records. No LLM, no network.

Used by budget.py (where the tokens went), worker.py (plugin profiles, repeated requests) and nothing else.
"""
import glob, json, os, pathlib, re, sys, time, unicodedata

PROJECTS = pathlib.Path.home() / '.claude' / 'projects'
HOME = pathlib.Path.home() / '.helena'
# machine-written prompts (subagents, hooks, other tools) are not the user's own requests
ROBOT = re.compile(r'^(<|\[|Another Claude|This session|You are|Worktree:|Caveat:)', re.I)


def plugin_of(tool):
    """'mcp__plugin_stripe_stripe__x' / Skill 'vercel:deploy' / Agent 'vercel:ai-architect' -> plugin name, else None."""
    m = re.match(r'mcp__plugin_([a-z0-9-]+?)_', tool)
    if m:
        return m.group(1)
    if ':' in tool and tool.split(':', 1)[0] in ('Skill', 'Agent'):
        name = tool.split(':', 1)[1]
        return name.split(':', 1)[0] if ':' in name else None
    return None


def sessions(days=30, since=0, pattern='*/*.jsonl'):
    """Yields one dict per transcript modified in the last `days` days (and after `since`, a unix time)."""
    limit = max(time.time() - days * 86400, since)
    for f in glob.glob(str(PROJECTS / pattern)):
        if os.path.getmtime(f) < limit:
            continue
        s = {'file': f, 'id': pathlib.Path(f).stem, 'cwd': None, 'prompts': [], 'tools': [], 'usage': [], 'outputs': []}
        last_prompt, calls = None, set()
        for line in open(f, encoding='utf-8', errors='ignore'):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            s['cwd'] = s['cwd'] or d.get('cwd')
            m = d.get('message') if isinstance(d.get('message'), dict) else {}
            c = m.get('content')
            if d.get('type') == 'user':
                if isinstance(c, str) and len(c) > 3 and not ROBOT.search(c.strip()):
                    last_prompt = {'text': c.strip(), 'ts': d.get('timestamp', ''), 'actions': []}
                    s['prompts'].append(last_prompt)
                elif isinstance(c, list):
                    for b in c:
                        if isinstance(b, dict) and b.get('type') == 'tool_result':
                            body = b.get('content')
                            if isinstance(body, list):  # an image is ~1.5k tokens whatever its base64 size: count ~4 chars/token
                                size = sum(len(x.get('text', '')) if x.get('type') == 'text' else 6000
                                           for x in body if isinstance(x, dict))
                            else:
                                size = len(body or '')
                            s['outputs'].append((b.get('tool_use_id'), size))
            elif d.get('type') == 'assistant':
                u = m.get('usage')
                # one API call is written as one line per content block, each repeating the same usage: count it once
                if u and m.get('id') not in calls:
                    calls.add(m.get('id') or len(s['usage']))  # no id: every line counts
                    made = u.get('cache_creation') or {}  # how long what this call wrote to the cache lives, in seconds
                    s['usage'].append({'ts': d.get('timestamp', ''), 'model': m.get('model', ''),
                                       'ttl': 3600 if made.get('ephemeral_1h_input_tokens') else 300 if made.get('ephemeral_5m_input_tokens') else 0,
                                       'input': u.get('input_tokens', 0), 'write': u.get('cache_creation_input_tokens', 0),
                                       'read': u.get('cache_read_input_tokens', 0), 'output': u.get('output_tokens', 0)})
                for b in c or []:
                    if not isinstance(b, dict) or b.get('type') != 'tool_use':
                        continue
                    name, inp = b.get('name', ''), b.get('input') or {}
                    if name == 'Skill':
                        name = f"Skill:{inp.get('skill', '')}"
                    elif name in ('Agent', 'Task'):
                        name = f"Agent:{inp.get('subagent_type', '')}"
                    s['tools'].append((b.get('id'), name, inp))
                    if last_prompt is not None and len(last_prompt['actions']) < 12:
                        what = inp.get('command') or inp.get('file_path') or inp.get('pattern') or inp.get('skill') or ''
                        last_prompt['actions'].append(f"{name}: {str(what)[:160]}")
        yield s


def subagents(days=30):
    """Subagent transcripts (<session>/subagents/agent-*.jsonl), each with the model / effort / type it was started with.

    Claude Code keeps them next to the parent session and `/usage` does not show their cache reads.
    """
    for s in sessions(days, pattern='*/*/subagents/agent-*.jsonl'):
        try:
            s['meta'] = json.loads(pathlib.Path(s['file']).with_suffix('.meta.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            s['meta'] = {}
        yield s


def fold(s):
    """Lower case, accents off, same length as the input (so a match position in the folded text fits the original)."""
    return ''.join(unicodedata.normalize('NFD', c)[0] for c in s).lower()


def recall(words, days=30, project=None, limit=20, around=300):
    """Turns (a user prompt plus what the AI answered) of the last `days` days that contain every word, newest first.

    One pass per file, line by line; a file whose raw text lacks the first word is skipped before any JSON is parsed.
    Only matching turns are kept. Returns dicts: date, project, id, text (about `around` chars around the first word, key-shaped strings masked).
    """
    from distill import SECRET  # the one mask the notes use; imported late so budget.py etc. do not pay for it
    words = [fold(w) for w in words if w.strip()]
    if not words:
        return []
    strip = lambda s: re.sub(r'[̀-ͯ]', '', unicodedata.normalize('NFD', re.sub(  # also reads JSON-escaped accents (ã)
        r'\\u00([c-f][0-9a-f])', lambda m: chr(int(m[1], 16)), s) if '\\u00' in s else s)).lower()
    hits, limit_t = [], time.time() - days * 86400
    for f in glob.glob(str(PROJECTS / '*/*.jsonl')):
        if os.path.getmtime(f) < limit_t:
            continue
        raw = pathlib.Path(f).read_text(encoding='utf-8', errors='ignore')
        if words[0] not in strip(raw):
            continue
        cwd, turn = None, None  # turn = [timestamp, prompt, assistant text so far]

        def close():
            if turn is None:
                return
            text = turn[1] + '\n> ' + turn[2] if turn[2] else turn[1]
            low = fold(text)
            name = re.split(r'[\\/]', (cwd or '').rstrip('\\/'))[-1] or '?'
            if all(w in low for w in words) and (not project or fold(project) == fold(name)):
                i = max(0, low.index(words[0]) - around // 3)
                hits.append({'date': turn[0][:10], 'ts': turn[0], 'project': name, 'id': pathlib.Path(f).stem,
                             'text': SECRET.sub('***', ' '.join(text[i:i + around].split()))})
        for line in raw.splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            cwd = cwd or d.get('cwd')
            m = d.get('message') if isinstance(d.get('message'), dict) else {}
            c = m.get('content')
            if d.get('type') == 'user' and isinstance(c, str) and len(c) > 3 and not ROBOT.search(c.strip()):
                close()
                turn = [d.get('timestamp', ''), c.strip(), '']
            elif d.get('type') == 'assistant' and turn is not None and isinstance(c, list) and len(turn[2]) < 4000:  # cap per turn
                turn[2] += ' '.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
        close()
    return sorted(hits, key=lambda h: h['ts'], reverse=True)[:limit]


def ledger(event):
    """Helena's own spending (distillation, worker), so the budget report can show net savings."""
    HOME.mkdir(exist_ok=True)
    with open(HOME / 'ledger.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), **event}) + '\n')


if __name__ == '__main__':  # python history.py recall <words...> [--days N] [--project name]
    sys.stdout.reconfigure(encoding='utf-8')
    a, opts = sys.argv[2:], {}
    for k in ('--days', '--project'):
        if k in a:
            i = a.index(k)
            opts[k], a = (a[i + 1] if i + 1 < len(a) else ''), a[:i] + a[i + 2:]
    if sys.argv[1:2] != ['recall'] or not a:
        sys.exit('usage: history.py recall <words...> [--days N] [--project name]')
    found = recall(a, int(opts.get('--days') or 30), opts.get('--project'))
    for h in found:
        print(f"{h['date']}  {h['project']}  {h['id'][:8]}\n{h['text']}\n")
    if not found:
        print(f"Nothing found for: {' '.join(a)}")
