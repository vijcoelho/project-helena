"""Tests diet.py's MCP server accounting (--probe-mcp, --off-mcp) and ALWAYS/NEVER directive count, no LLM.

    python eval/test_diet.py
"""
import json, os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'helena'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)


with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    home, d = tmp / 'home', tmp / 'proj'
    (home / '.claude' / 'projects' / 'p').mkdir(parents=True)
    d.mkdir()
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home))

    # A tiny real stdio MCP server to test --probe-mcp without network or external binaries
    mock = d / 'mock_mcp.py'
    mock.write_text(
        'import json, sys\n'
        'for line in sys.stdin:\n'
        '    m = json.loads(line)\n'
        '    if m.get("method") == "initialize":\n'
        '        print(json.dumps({"jsonrpc":"2.0","id":m["id"],"result":{"protocolVersion":"2025-06-18","capabilities":{"tools":{}}}}), flush=True)\n'
        '    elif m.get("method") == "tools/list":\n'
        '        tools = [{"name": f"tool_{i}", "description": "desc " * 20, "inputSchema": {"type": "object"}} for i in range(6)]\n'
        '        print(json.dumps({"jsonrpc":"2.0","id":m["id"],"result":{"tools":tools}}), flush=True)\n',
        encoding='utf-8',
    )
    (d / '.mcp.json').write_text(json.dumps({
        'mcpServers': {
            'idle-mcp': {'command': sys.executable, 'args': [str(mock)]},
            'used-mcp': {'command': sys.executable, 'args': [str(mock)]},
        }
    }), encoding='utf-8')
    (home / '.claude.json').write_text(json.dumps({
        'mcpServers': {'global-mcp': {'url': 'https://example.invalid/mcp'}}
    }), encoding='utf-8')
    (home / '.claude' / 'projects' / 'p' / 's.jsonl').write_text(
        '{"name":"mcp__used-mcp__tool_0","input":{}}\n' * 4, encoding='utf-8'
    )

    diet = lambda *a: subprocess.run(
        [sys.executable, str(ROOT / 'diet.py'), *a], cwd=d, capture_output=True, text=True, encoding='utf-8', env=env
    )

    # 1. Default run: instant estimate (~3.0k), counts uses, suggests --off-mcp for idle project server and claude mcp remove for global
    r = diet()
    check(r.returncode == 0, f'diet failed: {r.stderr}')
    check('mcp idle-mcp (project): est. (run --probe-mcp)' in r.stdout, f'idle mcp missing: {r.stdout!r}')
    check('--off-mcp idle-mcp' in r.stdout, f'--off-mcp hint missing: {r.stdout!r}')
    check('    4  mcp used-mcp (project):' in r.stdout and '--off-mcp used-mcp' not in r.stdout, f'used mcp count wrong: {r.stdout!r}')
    check('mcp global-mcp (user):' in r.stdout and 'claude mcp remove global-mcp' in r.stdout, f'global mcp hint missing: {r.stdout!r}')

    # 2. --probe-mcp: measures exact schema via tools/list and caches it in ~/.helena/mcp-schemas.json
    r2 = diet('--probe-mcp')
    check(r2.returncode == 0 and 'mcp idle-mcp (project): 6 tools' in r2.stdout, f'--probe-mcp did not measure tools: {r2.stdout!r}')
    cache = json.loads((home / '.helena' / 'mcp-schemas.json').read_text(encoding='utf-8'))
    check('idle-mcp' in cache and cache['idle-mcp']['tools'] == 6 and cache['idle-mcp']['tokens'] > 100, f'cache invalid: {cache!r}')
    # Subsequent default run reuses the cache without --probe-mcp
    r3 = diet()
    check('mcp idle-mcp (project): 6 tools' in r3.stdout, f'cached schema not reused: {r3.stdout!r}')

    # 3. --off-mcp: disables project server in .claude/settings.local.json; global prints remove command without touching ~/.claude.json
    off_p = diet('--off-mcp', 'idle-mcp')
    check(off_p.returncode == 0 and 'is off in this project' in off_p.stdout, f'--off-mcp project failed: {off_p.stdout!r}')
    local_cfg = json.loads((d / '.claude' / 'settings.local.json').read_text(encoding='utf-8'))
    check('idle-mcp' in local_cfg.get('disabledMcpjsonServers', []), f'disabledMcpjsonServers not set: {local_cfg!r}')
    check('mcp idle-mcp' not in diet().stdout, 'disabled MCP still listed in diet')
    off_g = diet('--off-mcp', 'global-mcp')
    check(off_g.returncode == 0 and 'claude mcp remove global-mcp' in off_g.stdout, f'--off-mcp global failed: {off_g.stdout!r}')

    # 4. lint(): >= 25 ALWAYS/NEVER directives triggers a report-only warning; < 25 stays silent
    (d / 'CLAUDE.md').write_text('\n'.join(f'Rule {i}: ALWAYS check X and NEVER skip Y.' for i in range(13)), encoding='utf-8')
    out_abs = diet().stdout
    check('26 ALWAYS/NEVER directives' in out_abs and 'ignoring half' in out_abs, f'ALWAYS/NEVER lint missing: {out_abs!r}')
    (d / 'CLAUDE.md').write_text('\n'.join(f'Rule {i}: always check X.' for i in range(5)), encoding='utf-8')
    check('ALWAYS/NEVER directives' not in diet().stdout, 'ALWAYS/NEVER lint fired below 25')

for e in errors:
    print('failed:', e)
print(f'{len(errors)} error(s)' if errors else 'PASS  test_diet')
sys.exit(1 if errors else 0)
