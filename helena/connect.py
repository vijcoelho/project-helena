"""Connects Helena to every AI CLI installed on this machine: same memory, same library, whatever model answers.

    python helena/connect.py            # connect every CLI found
    python helena/connect.py --remove   # undo it

Codex reads Claude Code plugins, so it gets the whole plugin (hooks included) plus the MCP server.
The others get helena/mcp.js through their own `mcp add`, and the "how to use Helena" block in their global
instruction file. Any other MCP client (Cursor, Claude Desktop, Windsurf, LM Studio...): paste the JSON printed at the end.
Models with no CLI of their own (Llama, DeepSeek, Grok via API...) work through opencode, which runs any provider.
"""
import json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
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


def main(remove=False):
    text = None if remove else subprocess.run(['node', MCP, '--instructions'], capture_output=True, text=True, encoding='utf-8').stdout.strip()
    found = 0
    for name, (add, rm, notes) in CLIS.items():
        if not shutil.which(name):
            continue
        found += 1
        run(name, *rm)  # add is not idempotent everywhere: start clean
        ok, why = run(name, *add) if not remove else (True, [''])
        if name == 'codex':  # Codex reads this repo as a Claude Code marketplace: hooks, commands and all
            steps = [['plugin', 'remove', 'helena@helena']] if remove else [['plugin', 'marketplace', 'add', str(REPO)],
                                                                             ['plugin', 'add', 'helena@helena']]
            for s in steps:
                ok2, why2 = run(name, *s)
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
    print(f'{found} CLI(s) {"disconnected" if remove else "connected"}. Restart them to load Helena.')
    if not remove:
        print('Any other MCP client, paste this into its MCP config:\n' +
              json.dumps({'mcpServers': {'helena': {'command': 'node', 'args': [MCP]}}}, indent=2))


if __name__ == '__main__':
    main('--remove' in sys.argv)
