"""Connects Helena to every AI CLI installed on this machine: same memory, same library, whatever model answers.

    python helena/connect.py            # connect every CLI found (+ native hooks for Codex and Cursor)
    python helena/connect.py --cursor   # also write ~/.cursor/hooks.json and ~/.cursor/mcp.json even if ~/.cursor is new
    python helena/connect.py --remove   # undo it

Codex gets native ~/.codex/hooks.json (only the 5 events Codex supports, no Claude-only `modules`) plus helena/mcp.js
and the ~/.codex/AGENTS.md block. Cursor (when ~/.cursor exists or --cursor is passed) gets both hooks and MCP.
The others get helena/mcp.js through their own `mcp add`, and the "how to use Helena" block in their global
instruction file. Any other MCP client (Claude Desktop, Windsurf, LM Studio...): paste the JSON printed at the end.
Models with no CLI of their own (Llama, DeepSeek, Grok via API...) work through opencode, which runs any provider.
"""
import json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
HOOKS = ROOT / 'hooks'
MCP = str(ROOT / 'mcp.js')
H = pathlib.Path.home()
START, END = '<!-- helena:start -->', '<!-- helena:end -->'

# name: (mcp add argv, mcp remove argv, global instruction file or None)
CLIS = {
    'codex': (['mcp', 'add', 'helena', '--', 'node', MCP], ['mcp', 'remove', 'helena'], H / '.codex' / 'AGENTS.md'),
    'gemini': (['mcp', 'add', '-s', 'user', 'helena', 'node', MCP], ['mcp', 'remove', '-s', 'user', 'helena'], H / '.gemini' / 'GEMINI.md'),
    'qwen': (['mcp', 'add', '-s', 'user', 'helena', 'node', MCP], ['mcp', 'remove', '-s', 'user', 'helena'], H / '.qwen' / 'QWEN.md'),
    'agy': (['mcp', 'add', 'helena', 'node', MCP], ['mcp', 'remove', 'helena'], H / '.gemini' / 'GEMINI.md'),
    # no global instruction file known for these two: the server's own MCP instructions tell the model what to do
    'kimi': (['mcp', 'add', '--transport', 'stdio', 'helena', '--', 'node', MCP], ['mcp', 'remove', 'helena'], None),
    'grok': (['mcp', 'add', 'helena', '--transport', 'stdio', '--command', 'node', '--args', MCP], ['mcp', 'remove', 'helena'], None),
}
OPENCODE = H / '.config' / 'opencode'
CURSOR = H / '.cursor'


def _hook_cmd(script):
    return f'node "{(HOOKS / script).as_posix()}"'


def portable_hooks():
    """Clean 5-event hooks map accepted by Codex CLI (>=0.117) and Cursor, with no Claude-only `modules` or extra events."""
    cmd = lambda s, **extra: {'type': 'command', 'command': _hook_cmd(s), **extra}
    return {
        'SessionStart': [{'hooks': [cmd('start.js')]}],
        'UserPromptSubmit': [{'hooks': [cmd('router.js')]}],
        'PreToolUse': [
            {'matcher': 'Bash', 'hooks': [cmd('guard.js'), cmd('trim.js'), cmd('gate.js', timeout=15)]},
            {'matcher': 'Read|Grep|Edit|Write|MultiEdit|mcp__.*', 'hooks': [cmd('gate.js', timeout=15)]},
        ],
        'PostToolUse': [
            {'matcher': 'Bash', 'hooks': [cmd('outside.js'), cmd('squeeze.js')]},
            {'matcher': 'WebFetch|WebSearch|mcp__.*', 'hooks': [cmd('outside.js'), cmd('squeeze.js')]},
            {'matcher': 'Edit|Write|MultiEdit', 'hooks': [cmd('nudge.js')]},
        ],
        'Stop': [{'hooks': [cmd('done.js', timeout=300)]}],
    }


def _is_helena_group(group):
    hs = group.get('hooks') if isinstance(group, dict) else None
    if not isinstance(hs, list) or not hs:
        return False
    return all(isinstance(h, dict) and 'helena/hooks/' in str(h.get('command', '')).replace('\\', '/').lower() for h in hs)


def sync_hooks_file(target, remove=False):
    """Merges (or removes) Helena's portable hooks in `target` (e.g. ~/.codex/hooks.json), leaving user hooks intact."""
    try:
        data = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    except (OSError, ValueError):
        return False, [f'{target} is not valid JSON']
    if not isinstance(data, dict):
        data = {}
    hooks = data.get('hooks') if isinstance(data.get('hooks'), dict) else {}
    for ev_name in list(hooks.keys()):
        if isinstance(hooks[ev_name], list):
            hooks[ev_name] = [g for g in hooks[ev_name] if not _is_helena_group(g)]
            if not hooks[ev_name]:
                del hooks[ev_name]
    if not remove:
        for ev_name, groups in portable_hooks().items():
            hooks.setdefault(ev_name, []).extend(groups)
    if hooks:
        data['hooks'] = hooks
    else:
        data.pop('hooks', None)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return True, ['']


def cursor_setup(remove=False):
    """Installs (or removes) Helena's hooks in ~/.cursor/hooks.json and MCP server in ~/.cursor/mcp.json."""
    ok_h, why_h = sync_hooks_file(CURSOR / 'hooks.json', remove)
    mcp_file = CURSOR / 'mcp.json'
    try:
        conf = json.loads(mcp_file.read_text(encoding='utf-8')) if mcp_file.exists() else {}
    except (OSError, ValueError):
        return False, [f'{mcp_file} is not valid JSON']
    servers = conf.setdefault('mcpServers', {})
    if remove:
        servers.pop('helena', None)
    else:
        servers['helena'] = {'command': 'node', 'args': [MCP]}
    mcp_file.parent.mkdir(parents=True, exist_ok=True)
    mcp_file.write_text(json.dumps(conf, indent=2) + '\n', encoding='utf-8')
    return ok_h, why_h


def run(*argv):
    exe = shutil.which(argv[0])
    r = subprocess.run([exe, *argv[1:]], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    return r.returncode == 0, (r.stderr or r.stdout).strip().splitlines()[-1:] or ['']


def block(f, text):
    """Writes (or with text=None removes) Helena's block in an instruction file, leaving the rest of the file alone."""
    old = f.read_text(encoding='utf-8') if f.exists() else ''
    new = re.sub(rf'\n*{START}.*?{END}\n?', '\n', old, flags=re.S).strip()
    if text:
        new = (new + '\n\n' if new else '') + f'{START}\n# Helena\n\n{text}\n{END}'
    if new.strip() != old.strip():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(new + '\n', encoding='utf-8')


def opencode(remove):
    f = next((p for p in (OPENCODE / 'opencode.json', OPENCODE / 'opencode.jsonc') if p.exists()), OPENCODE / 'opencode.json')
    try:
        conf = json.loads(f.read_text(encoding='utf-8')) if f.exists() else {'$schema': 'https://opencode.ai/config.json'}
    except ValueError:
        return False, [f'{f} has comments; add "mcp": {{"helena": {{"type": "local", "command": ["node", "{MCP}"]}}}} by hand']
    mcp = conf.setdefault('mcp', {})
    if remove:
        mcp.pop('helena', None)
    else:
        mcp['helena'] = {'type': 'local', 'command': ['node', MCP], 'enabled': True}
    f.write_text(json.dumps(conf, indent=2) + '\n', encoding='utf-8')
    return True, ['']


def main(remove=False, want_cursor=False):
    text = None if remove else subprocess.run(['node', MCP, '--instructions'], capture_output=True, text=True, encoding='utf-8').stdout.strip()
    found = 0
    for name, (add, rm, notes) in CLIS.items():
        if not shutil.which(name):
            continue
        found += 1
        run(name, *rm)  # add is not idempotent everywhere: start clean
        ok, why = run(name, *add) if not remove else (True, [''])
        if name == 'codex':
            # Write Codex-native ~/.codex/hooks.json (5 supported events, no Claude-only `modules`) and remove any old Claude plugin entry
            run(name, 'plugin', 'remove', 'helena@helena')
            ok2, why2 = sync_hooks_file(H / '.codex' / 'hooks.json', remove)
            ok, why = ok and ok2, why if ok2 else why2
        if notes and ok:
            block(notes, text)
        print(f"{'ok ' if ok else 'ERR'} {name}{'' if ok else ': ' + why[0]}")
    if shutil.which('opencode') or OPENCODE.exists():
        found += 1
        ok, why = opencode(remove)
        if ok:
            block(OPENCODE / 'AGENTS.md', text)
        print(f"{'ok ' if ok else 'ERR'} opencode{'' if ok else ': ' + why[0]}")
    if want_cursor or CURSOR.exists():
        found += 1
        ok, why = cursor_setup(remove)
        print(f"{'ok ' if ok else 'ERR'} cursor{'' if ok else ': ' + why[0]}")
    print(f'{found} CLI(s) {"disconnected" if remove else "connected"}. Restart them to load Helena.')
    if not remove:
        print('Any other MCP client, paste this into its MCP config:\n' +
              json.dumps({'mcpServers': {'helena': {'command': 'node', 'args': [MCP]}}}, indent=2))


if __name__ == '__main__':
    main('--remove' in sys.argv, '--cursor' in sys.argv)
