"""helena-mcp + Codex transcripts, no LLM: python eval/test_mcp.py

The MCP server handshakes, saves a note into a temp vault (secret masked), finds it again for a matching request,
and distill reads a Codex rollout like a Claude transcript.
"""
import json, os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'helena'))
import distill

KEY = 'sk_' + 'live_' + 'FAKE' * 6  # assembled here so this file does not trip secret scanners (same as test_guard.py)

with tempfile.TemporaryDirectory() as vault:
    calls = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
        {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'helena_remember', 'arguments': {
            'slug': 'deploy-coolify', 'type': 'rule', 'description': 'deploy do zebrafish sempre pelo coolify',
            'body': 'Nunca pela Vercel. Token ' + KEY}}},
        {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'helena_context', 'arguments': {
            'request': 'como faço o deploy do zebrafish no coolify?', 'cwd': vault}}},
        {'jsonrpc': '2.0', 'id': 5, 'method': 'nope'},
        {'jsonrpc': '2.0', 'id': 6, 'method': 'tools/call', 'params': {'name': 'helena_recall', 'arguments': {'words': 'zzqxj' + 'nonexistent', 'days': '1'}}},
    ]
    r = subprocess.run(['node', str(ROOT / 'helena' / 'mcp.js')], input='\n'.join(map(json.dumps, calls)) + '\n',
                       capture_output=True, text=True, encoding='utf-8', timeout=60,
                       env=dict(os.environ, HELENA_VAULT=vault, HELENA_EVAL='1'))
    out = {d['id']: d for d in map(json.loads, r.stdout.splitlines())}
    assert out[1]['result']['serverInfo']['name'] == 'helena', out[1]
    assert {t['name'] for t in out[2]['result']['tools']} == {'helena_start', 'helena_context', 'helena_skill', 'helena_remember', 'helena_limits', 'helena_rewind', 'helena_recall'}
    assert 'Nothing found' in out[6]['result']['content'][0]['text'], out[6]  # no real session mentions this
    assert 'Saved' in out[3]['result']['content'][0]['text'], out[3]
    note = (pathlib.Path(vault) / 'Memory' / 'deploy-coolify.md').read_text(encoding='utf-8')
    assert KEY not in note and '***' in note, note
    assert 'Nunca pela Vercel' in out[4]['result']['content'][0]['text'], out[4]
    assert out[5]['error']['code'] == -32601

with tempfile.TemporaryDirectory() as tmp:
    rollout = pathlib.Path(tmp) / 'rollout.jsonl'
    msg = lambda role, kind, text: {'type': 'response_item', 'payload': {'type': 'message', 'role': role, 'content': [{'type': kind, 'text': text}]}}
    rollout.write_text('\n'.join(json.dumps(x) for x in [
        {'type': 'session_meta', 'timestamp': '2026-10-06T10:00:00Z', 'payload': {'cwd': tmp}},
        msg('user', 'input_text', '# AGENTS.md instructions for C:/x'),
        msg('user', 'input_text', '<environment_context>...</environment_context>'),
        msg('user', 'input_text', 'usa pnpm, não npm'),
        msg('assistant', 'output_text', 'Certo, troco para pnpm.'),
    ]), encoding='utf-8')
    assert distill.turns(rollout) == ['USER: usa pnpm, não npm', 'AI: Certo, troco para pnpm.'], distill.turns(rollout)
    assert distill.project_of(rollout)[0] == pathlib.Path(tmp).name

print('ok: mcp handshake, remember (secret masked), context finds the note, Codex rollout parsed')
