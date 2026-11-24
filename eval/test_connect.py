"""Tests connect.py's portable hooks generation for Codex CLI (~/.codex/hooks.json) and Cursor (~/.cursor/hooks.json +
mcp.json): preserves user hooks, uses only the 5 portable events with no Claude-only `modules`, and cleanly removes.

    python eval/test_connect.py
"""
import json, pathlib, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'helena'))
import connect

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    codex_hooks = tmp / '.codex' / 'hooks.json'
    codex_hooks.parent.mkdir(parents=True)
    # Pre-existing user hook must be preserved across install and --remove
    codex_hooks.write_text(json.dumps({
        'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo user-stop'}]}]}
    }), encoding='utf-8')

    ok, why = connect.sync_hooks_file(codex_hooks, remove=False)
    assert ok, why
    data = json.loads(codex_hooks.read_text(encoding='utf-8'))
    assert 'modules' not in data, 'Codex hooks.json must not contain Claude-only modules'
    assert set(data['hooks'].keys()) == {'SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'Stop'}, data['hooks'].keys()
    # No unsupported handler keys (`if`, `async`) in portable hooks
    for groups in data['hooks'].values():
        for g in groups:
            for h in g['hooks']:
                assert 'if' not in h and 'async' not in h, h
    assert any(h['command'] == 'echo user-stop' for g in data['hooks']['Stop'] for h in g['hooks']), 'user hook lost'
    # Idempotent: running twice must not duplicate Helena groups
    connect.sync_hooks_file(codex_hooks, remove=False)
    data2 = json.loads(codex_hooks.read_text(encoding='utf-8'))
    assert len(data2['hooks']['Stop']) == 2, data2['hooks']['Stop']  # 1 user + 1 helena
    # Remove leaves only the user hook
    connect.sync_hooks_file(codex_hooks, remove=True)
    data3 = json.loads(codex_hooks.read_text(encoding='utf-8'))
    assert list(data3['hooks'].keys()) == ['Stop'] and len(data3['hooks']['Stop']) == 1, data3

    # Cursor setup: hooks.json + mcp.json merge and remove
    connect.CURSOR = tmp / '.cursor'
    connect.CURSOR.mkdir()
    (connect.CURSOR / 'mcp.json').write_text(json.dumps({'mcpServers': {'other': {'command': 'x'}}}), encoding='utf-8')
    ok, why = connect.cursor_setup(remove=False)
    assert ok, why
    cmcp = json.loads((connect.CURSOR / 'mcp.json').read_text(encoding='utf-8'))
    assert 'helena' in cmcp['mcpServers'] and 'other' in cmcp['mcpServers'], cmcp
    assert (connect.CURSOR / 'hooks.json').exists()
    connect.cursor_setup(remove=True)
    cmcp2 = json.loads((connect.CURSOR / 'mcp.json').read_text(encoding='utf-8'))
    assert 'helena' not in cmcp2['mcpServers'] and 'other' in cmcp2['mcpServers'], cmcp2

print('PASS  test_connect')
