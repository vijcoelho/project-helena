"""What sits in the context before you type anything, piece by piece, and how often each piece was used.

    python helena/diet.py [days]            # the list (uses counted over the last 30 days by default)
    python helena/diet.py --probe-mcp       # also query stdio MCP servers (tools/list) and cache their real schema size
    python helena/diet.py --off <plugin>    # turn a plugin off in this project only (.claude/settings.local.json)
    python helena/diet.py --off-mcp <name>  # turn a project .mcp.json server off here (or print the remove command)

Every skill, command, agent and MCP server puts its names/schemas in the context of every message, used or not; a
CLAUDE.md goes in whole. This adds them up per plugin, folder, file and MCP server (4 characters ~ 1 token: an estimate,
the measured total is the "Fixed context" line of /helena:budget) and counts, from your own transcripts, how many times
each was called. No LLM, nothing is changed without --off / --off-mcp.
"""
import hashlib, json, os, pathlib, re, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from worker import load, save  # noqa: E402

CLAUDE = pathlib.Path.home() / '.claude'
HELENA = pathlib.Path.home() / '.helena'
MCP_CACHE = HELENA / 'mcp-schemas.json'
MCP_MEDIAN = 2960  # testedmcp 2026-11 median tokens per MCP server before first call
tok = lambda chars: round(chars / 4)
k = lambda n: f'{n / 1000:.1f}k' if n >= 1000 else str(n)


def _norm(p):
    return os.path.normcase(os.path.normpath(str(pathlib.Path(p).resolve())))


def _cfg_hash(cfg):
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode('utf-8')).hexdigest()[:12]


def mcp_servers(cwd):
    """Configured MCP servers visible in `cwd`: [{name, scope, cfg, hash}]. Project overrides user; disabled ones skipped."""
    home = pathlib.Path.home()
    local_settings = load(cwd / '.claude' / 'settings.local.json', {})
    disabled = set(local_settings.get('disabledMcpjsonServers') or []) | set(local_settings.get('disabledMcpServers') or [])
    found = {}
    claude_json = load(home / '.claude.json', {})
    for name, cfg in (claude_json.get('mcpServers') or {}).items():
        if isinstance(cfg, dict):
            found[name] = {'name': name, 'scope': 'user', 'cfg': cfg, 'hash': _cfg_hash(cfg)}
    want = _norm(cwd)
    for proj_path, pdata in (claude_json.get('projects') or {}).items():
        if isinstance(pdata, dict) and _norm(proj_path) == want:
            for name, cfg in (pdata.get('mcpServers') or {}).items():
                if isinstance(cfg, dict):
                    found[name] = {'name': name, 'scope': 'local', 'cfg': cfg, 'hash': _cfg_hash(cfg)}
            disabled |= set(pdata.get('disabledMcpjsonServers') or []) | set(pdata.get('disabledMcpServers') or [])
    proj_mcp = load(cwd / '.mcp.json', {})
    for name, cfg in (proj_mcp.get('mcpServers') or proj_mcp).items():
        if isinstance(cfg, dict) and ('command' in cfg or 'url' in cfg or 'type' in cfg):
            found[name] = {'name': name, 'scope': 'project', 'cfg': cfg, 'hash': _cfg_hash(cfg)}
    settings = load(CLAUDE / 'settings.json', {})
    installed = load(CLAUDE / 'plugins' / 'installed_plugins.json', {}).get('plugins', {})
    on = {**settings.get('enabledPlugins', {}), **load(cwd / '.claude' / 'settings.json', {}).get('enabledPlugins', {}), **local_settings.get('enabledPlugins', {})}
    for key, enabled in on.items():
        root = pathlib.Path((installed.get(key) or [{}])[0].get('installPath', ''))
        if not enabled or not root.is_dir():
            continue
        pmcp = load(root / '.mcp.json', {}) or load(root / '.claude-plugin' / 'plugin.json', {})
        for name, cfg in (pmcp.get('mcpServers') or {}).items():
            if isinstance(cfg, dict):
                pname = key.split('@')[0]
                found.setdefault(f'plugin:{pname}:{name}', {'name': name, 'plugin': pname, 'scope': 'plugin', 'cfg': cfg, 'hash': _cfg_hash(cfg)})
    return [s for s in found.values() if s['name'] not in disabled]


def probe_mcp(server, timeout=3.0):
    """Queries a stdio MCP server with initialize + tools/list and returns {'tokens': int, 'tools': int} or None."""
    cfg = server.get('cfg') or {}
    cmd = cfg.get('command')
    if not cmd:
        return None
    argv = [cmd, *(cfg.get('args') or [])]
    env = {**os.environ, **{str(k): str(v) for k, v in (cfg.get('env') or {}).items()}}
    msgs = (json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'helena-diet', 'version': '1'}}}) + '\n' +
            json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}}) + '\n' +
            json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}) + '\n')
    kw = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)} if os.name == 'nt' else {}
    try:
        r = subprocess.run(argv, input=msgs, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=timeout, env=env, **kw)
        raw = r.stdout
    except subprocess.TimeoutExpired as e:
        raw = (e.stdout or b'').decode('utf-8', 'ignore') if isinstance(e.stdout, bytes) else (e.stdout or '')
    except OSError:
        return None
    for line in raw.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get('id') == 2 and isinstance(d.get('result'), dict) and isinstance(d['result'].get('tools'), list):
            tools = d['result']['tools']
            return {'tokens': tok(len(json.dumps(tools))), 'tools': len(tools)}
    return None


def described(folder, pattern):
    """[(name, characters its listing takes)] for the skills, commands or agents under a folder."""
    out = []
    for f in sorted(folder.glob(pattern)) if folder.is_dir() else []:
        head = f.read_text(encoding='utf-8', errors='ignore')[:3000]
        if re.search(r'^disable-model-invocation:\s*true', head, re.M):
            continue  # not listed to the model: costs nothing until the user types it
        desc = (re.search(r'^description:\s*(.+)$', head, re.M) or [None, ''])[1]
        name = (re.search(r'^name:\s*(.+)$', head, re.M) or [None, f.parent.name if f.name == 'SKILL.md' else f.stem])[1].strip()
        out.append((name, len(name) + len(desc) + 8))
    return out


def pieces(cwd):
    settings, local = load(CLAUDE / 'settings.json', {}), load(cwd / '.claude' / 'settings.local.json', {})
    installed = load(CLAUDE / 'plugins' / 'installed_plugins.json', {}).get('plugins', {})
    on = {**settings.get('enabledPlugins', {}), **load(cwd / '.claude' / 'settings.json', {}).get('enabledPlugins', {}), **local.get('enabledPlugins', {})}
    for key, enabled in on.items():
        root = pathlib.Path((installed.get(key) or [{}])[0].get('installPath', ''))
        if not enabled or not root.is_dir():
            continue
        parts = {'skills': described(root / 'skills', '*/SKILL.md'), 'commands': described(root / 'commands', '*.md'), 'agents': described(root / 'agents', '*.md')}
        hooks = (root / 'hooks' / 'hooks.json').exists() or 'hooks' in load(root / '.claude-plugin' / 'plugin.json', {})
        yield {'kind': 'plugin', 'key': key, 'name': key.split('@')[0], 'hooks': hooks, 'parts': parts,
               'chars': sum(c for p in parts.values() for _, c in p)}
    for label, base in (('yours (~/.claude)', CLAUDE), ('this project (.claude)', cwd / '.claude')):
        parts = {'skills': described(base / 'skills', '*/SKILL.md'), 'commands': described(base / 'commands', '*.md'), 'agents': described(base / 'agents', '*.md')}
        if any(parts.values()):
            yield {'kind': 'folder', 'name': label, 'parts': parts, 'chars': sum(c for p in parts.values() for _, c in p)}
    for f in (CLAUDE / 'CLAUDE.md', cwd / 'CLAUDE.md', cwd / 'AGENTS.md'):
        if f.is_file():
            yield {'kind': 'file', 'name': str(f).replace(str(pathlib.Path.home()), '~'), 'parts': {}, 'chars': f.stat().st_size}


def uses(days):
    """How many times each skill, agent type and MCP server was called, from transcripts changed in the last `days`."""
    n, since = {}, time.time() - days * 86400
    for f in (CLAUDE / 'projects').glob('**/*.jsonl'):
        if f.stat().st_mtime < since:
            continue
        raw = f.read_text(encoding='utf-8', errors='ignore')
        for m in re.finditer(r'"(?:skill|subagent_type)":"([^"]+)"', raw):
            n[m.group(1)] = n.get(m.group(1), 0) + 1
        for m in re.finditer(r'"name":"mcp__([^"\\]+?)__', raw):
            srv = m.group(1)
            n['mcp:' + srv] = n.get('mcp:' + srv, 0) + 1
            if srv.startswith('plugin_'):
                tail = srv.split('_')[-1]
                n['mcp:' + tail] = n.get('mcp:' + tail, 0) + 1
    return n


PROHIBIT = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\W*(?:don[’']t|do not|never|avoid|não|nunca|jamais|evite)\b", re.I)
ABSOLUTES = re.compile(r'\b(?:always|never|must|sempre|nunca|jamais)\b', re.I)
TREE = re.compile(r'├──|└──|│')


def runs(lines, hit, n):
    """[(first, last)] 1-based, for each run of at least n consecutive lines where hit(line)."""
    out, i = [], 0
    while i < len(lines):
        j = i
        while j < len(lines) and hit(lines[j]):
            j += 1
        if j - i >= n:
            out.append((i + 1, j))
        i = max(j, i + 1)
    return out


def lint(cwd):
    """Per instruction file: [(first line, last line, tokens, what, hint)] for what the repo already shows. Reports only."""
    scripts = load(cwd / 'package.json', {}).get('scripts', {})
    restates = lambda l: any(cmd in l and re.search(rf'\b(?:npm|pnpm|yarn|bun)(?: run)? {re.escape(n)}\b', l) for n, cmd in scripts.items() if cmd)
    for name in ('CLAUDE.md', 'AGENTS.md'):
        f = cwd / name
        if not f.is_file():
            continue
        text = f.read_text(encoding='utf-8', errors='ignore')
        lines = text.splitlines()
        found = [(a, b, 'npm script', '(package.json already says it)') for a, b in runs(lines, restates, 1)]
        found += [(a, b, 'directory tree', '(the repo shows it)') for a, b in runs(lines, TREE.search, 4)]
        found += [(a, b, 'prohibition list', '(a long "do not" list is followed less than three positive rules)') for a, b in runs(lines, PROHIBIT.search, 8)]
        rows = [(a, b, tok(sum(len(l) + 1 for l in lines[a - 1:b])), what, hint) for a, b, what, hint in found]
        n_abs = len(ABSOLUTES.findall(text))
        if n_abs >= 25:
            rows.append((1, len(lines), 0, f'{n_abs} ALWAYS/NEVER directives', '(past ~25, models start ignoring half — keep only rules that prevented real bugs)'))
        if rows:
            yield name, rows


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    cwd = pathlib.Path.cwd()
    if sys.argv[1:2] == ['--off']:
        want = sys.argv[2] if len(sys.argv) > 2 else ''
        key = next((p['key'] for p in pieces(cwd) if p['kind'] == 'plugin' and want in (p['key'], p['name'])), None)
        if not key:
            sys.exit(f'no enabled plugin named {want!r} here')
        f = cwd / '.claude' / 'settings.local.json'
        s = load(f, {})
        s.setdefault('enabledPlugins', {})[key] = False
        f.parent.mkdir(exist_ok=True)
        save(f, s)
        print(f'{key} is off in this project ({f}). It applies from the next session; delete that line to turn it back on.')
        return
    if sys.argv[1:2] == ['--off-mcp']:
        want = sys.argv[2] if len(sys.argv) > 2 else ''
        srv = next((s for s in mcp_servers(cwd) if s['name'] == want), None)
        if not srv:
            sys.exit(f'no enabled MCP server named {want!r} here')
        if srv['scope'] == 'project':
            f = cwd / '.claude' / 'settings.local.json'
            s = load(f, {})
            off = s.setdefault('disabledMcpjsonServers', [])
            if want not in off:
                off.append(want)
            f.parent.mkdir(exist_ok=True)
            save(f, s)
            print(f'MCP server {want} is off in this project ({f}). Applies from the next session; remove it from disabledMcpjsonServers to re-enable.')
        else:
            print(f'MCP server {want} is configured in {srv["scope"]} scope (~/.claude.json). To remove it safely, run: claude mcp remove {want}')
        return
    do_probe = '--probe-mcp' in sys.argv[1:]
    days = next((int(a) for a in sys.argv[1:] if a.isdigit()), 30)
    used, rows, total = uses(days), [], 0
    for p in pieces(cwd):
        names = [n for part in p['parts'].values() for n, _ in part]
        count = sum(used.get(n, 0) + (used.get(f"{p['name']}:{n}", 0) if p['kind'] == 'plugin' else 0) for n in names)
        idle = [n for n in names if not used.get(n) and not used.get(f"{p['name']}:{n}")]
        what = ', '.join(f'{len(v)} {w}' for w, v in p['parts'].items() if v)
        note = ''
        if p['kind'] == 'plugin':
            note = ' [has hooks: it works without being called]' if p['hooks'] else \
                f'  -> never called: python helena/diet.py --off {p["name"]}' if not count else ''
        elif p['kind'] == 'folder' and idle:
            note = f'  -> never called ({len(idle)}): ' + ', '.join(idle[:6]) + (' …' if len(idle) > 6 else '')
        elif p['kind'] == 'file' and p['chars'] > 12000:
            note = '  -> over ~3k tokens: rules that only matter sometimes cost less as memory notes'
        rows.append((tok(p['chars']), '-' if p['kind'] == 'file' else str(count), f"{p['kind']} {p['name']}" + (f': {what}' if what else ''), note))
        total += tok(p['chars'])
    mcps = mcp_servers(cwd)
    cache = load(MCP_CACHE, {})
    cache_dirty = False
    for s in mcps:
        cached = cache.get(s['name'])
        measured = cached if isinstance(cached, dict) and cached.get('hash') == s['hash'] else None
        if do_probe and not measured:
            got = probe_mcp(s)
            if got:
                measured = {**got, 'hash': s['hash']}
                cache[s['name']] = measured
                cache_dirty = True
        t = measured['tokens'] if measured else MCP_MEDIAN
        count = used.get('mcp:' + s['name'], 0)
        detail = f"{measured['tools']} tools" if measured else 'est. (run --probe-mcp)'
        action = (f'  -> never called: python helena/diet.py --off-mcp {s["name"]}' if s['scope'] == 'project'
                  else f'  -> never called: claude mcp remove {s["name"]}') if not count and s['scope'] != 'plugin' else ''
        rows.append((t, str(count), f"mcp {s['name']} ({s['scope']}): {detail}", action))
        total += t
    if cache_dirty:
        HELENA.mkdir(exist_ok=True)
        save(MCP_CACHE, cache)
    print(f'In the context before you type, re-read on every message (estimate: descriptions, 4 characters ~ 1 token; uses in {days} days)')
    print(f"  {'~tokens':>7} {'uses':>5}  piece")
    for t, c, name, note in sorted(rows, reverse=True):
        if t >= 20:
            print(f'  {k(t):>7} {c:>5}  {name}{note}')
    tail = 'The rest of the fixed context is the CLI itself (system prompt, built-in tool definitions).' if mcps else \
        'The rest of the fixed context is the CLI itself (system prompt, tool definitions) and MCP servers.'
    print(f'  {k(total):>7}        listed here. {tail}')
    print('--off / --off-mcp turns a plugin or project MCP off in this folder only; delete its line in .claude/settings.local.json to turn it back on.')
    for name, rows in lint(cwd):
        tok_cut = sum(r[2] for r in rows)
        hdr = f'\n{name}: ~{tok_cut} tokens could go (paid on every call):' if tok_cut else f'\n{name}: lint warnings (paid on every call):'
        print(hdr)
        for a, b, t, what, hint in rows:
            tstr = f', ~{t} tokens' if t else ''
            print(f'  lines {a}-{b}: {what}{tstr} {hint}')


if __name__ == '__main__':
    main()
