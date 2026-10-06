"""Reads Claude Code transcripts (~/.claude/projects/**/*.jsonl) into plain session records. No LLM, no network.

Used by budget.py (where the tokens went), worker.py (plugin profiles, repeated requests) and nothing else.
"""
import glob, json, os, pathlib, re, time

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


def sessions(days=30, since=0):
    """Yields one dict per transcript modified in the last `days` days (and after `since`, a unix time)."""
    limit = max(time.time() - days * 86400, since)
    for f in glob.glob(str(PROJECTS / '*' / '*.jsonl')):
        if os.path.getmtime(f) < limit:
            continue
        s = {'file': f, 'id': pathlib.Path(f).stem, 'cwd': None, 'prompts': [], 'tools': [], 'usage': [], 'outputs': []}
        last_prompt = None
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
                if u:
                    s['usage'].append({'ts': d.get('timestamp', ''), 'model': m.get('model', ''),
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


def ledger(event):
    """Helena's own spending (distillation, worker), so the budget report can show net savings."""
    HOME.mkdir(exist_ok=True)
    with open(HOME / 'ledger.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), **event}) + '\n')
