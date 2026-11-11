"""Helena 2.0's context pieces, without calling Claude:
squeeze.js (a long command output is folded and cut, the full text saved), start.js (the session start fits under the
CLI's 10,000-character hook cap, the memory index is a budget), compact.js, brief.js (what every worker is handed),
wave.js (a worktree's work lands in the main tree, a colliding patch does not).

    python eval/test_squeeze.py
"""
import json, os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent / 'helena'
errors = []


def check(ok, what):
    if not ok:
        errors.append(what)


with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    home, d = tmp / 'home', tmp / 'app'
    (home / '.helena').mkdir(parents=True)
    d.mkdir()
    env = dict(os.environ, USERPROFILE=str(home), HOME=str(home), HELENA_EVAL='1', HELENA_VAULT=str(home / 'vault'))

    def hook(name, ev, raw=False):
        r = subprocess.run(['node', str(ROOT / 'hooks' / name)], input=json.dumps({'cwd': str(d), 'session_id': 'sess1234', **ev}),
                           capture_output=True, text=True, encoding='utf-8', env=env, cwd=d, timeout=30)
        return r.stdout if raw else (json.loads(r.stdout) if r.stdout.strip() else {})

    def bash(stdout, stderr='', command='npm test', **more):
        out = hook('squeeze.js', {'tool_name': 'Bash', 'tool_input': {'command': command},
                                  'tool_response': {'stdout': stdout, 'stderr': stderr, 'interrupted': False, 'isImage': False, **more}})
        return (out.get('hookSpecificOutput') or {}).get('updatedToolOutput')

    # ---- squeeze: short output and output that would not shrink are left alone
    check(bash('ok\n' * 100) is None, 'squeeze: a short output was replaced')
    prose = '\n'.join(f'{"abcdefg"[i % 7] * (i % 40)} is a line that looks like no other line' for i in range(150))
    check(bash(prose) is None, 'squeeze: 9k of text with nothing to fold was replaced')
    # progress lines that differ only in their numbers fold into three
    progress = ''.join(f'Downloading package {i}/900 ({i * 3} kB)\n' for i in range(900)) + 'added 900 packages\n'
    got = bash(progress)
    check(got and 'similar lines' in got['stdout'] and len(got['stdout']) < 600, 'squeeze: 900 progress lines were not folded')
    check(got and 'added 900 packages' in got['stdout'] and 'Downloading package 0/900' in got['stdout'], 'squeeze: the first or last line was lost')
    check(got and got.get('interrupted') is False and got.get('stderr') == '', 'squeeze: the other fields of the result changed')
    # a long test log: head and tail stay, the failing line from the middle stays with its number, the rest is cut
    log = [f'test_{i:04d} {"abc"[i % 3]}{i * 7919 % 1000} ... ok ({"xyz"[i % 3]} suite)' for i in range(1500)]
    log[700] = 'test_0700 ... FAILED: expected 3, got 4'
    got = bash('\n'.join(log) + '\n== 1 failed, 1499 passed ==\n')
    s = got and got['stdout'] or ''
    check('FAILED: expected 3, got 4' in s and '701: ' in s, 'squeeze: the failing line in the middle was cut')
    check('1 failed, 1499 passed' in s and 'test_0000' in s and 'lines cut' in s, 'squeeze: head, tail or the cut marker is missing')
    check(len(s) < 12000, f'squeeze: a 1500-line log still takes {len(s)} characters')
    saved = list((home / '.helena' / 'out').glob('*.log'))
    check(saved and 'test_0900' in saved[-1].read_text(encoding='utf-8'), 'squeeze: the full output was not saved')
    check(saved and saved[-1].as_posix() in s, 'squeeze: the AI is not told where the full output is')
    trims = (home / '.helena' / 'trim.jsonl').read_text().splitlines()
    check(trims and json.loads(trims[-1])['tokens'] > 5000, 'squeeze: what was kept out is not counted in trim.jsonl')
    # escape hatch, content commands, images
    check(bash('\n'.join(log), command='npm test  # helena:full') is None, 'squeeze: helena:full was ignored')
    check(bash('\n'.join(log), isImage=True) is None, 'squeeze: an image result was touched')
    diff = '\n'.join(f'+ const v{i} = {"abc"[i % 3]}{i * 31 % 97};' for i in range(1200))   # ~28k characters of content
    check(bash(diff, command='git diff') is None, 'squeeze: a 28k git diff was cut (content commands are cut from 60k)')
    check(bash(diff, command='npm run build') is not None, 'squeeze: a 28k build log was left whole')
    # colour codes and \r progress
    got = bash('\x1b[32mPASS\x1b[0m\n' + 'a\rb\rdone 100%\n' + 'x' * 60 + '\n' + ''.join(f'chunk {i} built in {i}ms\n' for i in range(400)))
    check(got and '\x1b' not in got['stdout'] and 'done 100%' in got['stdout'] and 'a\r' not in got['stdout'], 'squeeze: colour codes or \\r progress survived')

    # ---- start.js: 200 notes and a long handoff still fit under the CLI cap, and the project's notes come first
    mem = home / 'vault' / 'Memory'
    mem.mkdir(parents=True)
    for i in range(200):
        (mem / f'note-{i:03d}.md').write_text(f'---\ntype: fact\ndescription: fact number {i} about something the user said once, long enough to be cut\n---\nbody\n')
    (mem / 'zz-mine.md').write_text('---\ntype: rule\ndescription: this project deploys with docker\nproject: app\n---\nbody\n')
    (mem / 'zz-hot.md').write_text('---\ntype: rule\ndescription: the note that is handed over most\n---\nbody\n')
    (home / '.helena' / 'stats.json').write_text(json.dumps({'notes': {'zz-hot': {'hits': 9}}, 'skills': {}}))
    (d / 'HANDOFF.md').write_text('## Done\n' + 'x\n' * 3000 + '## Next\n' + '- the next step\n' * 400 + '## Decisions\n- use sqlite, not postgres (rejected: one more container)\n')
    out = hook('start.js', {'source': 'startup', 'transcript_path': str(d / 't.jsonl')}, raw=True)
    check(len(out.encode('utf-8')) < 10000, f'start: the session start is {len(out.encode("utf-8"))} bytes, the CLI keeps a 2 KB preview past 10,000')
    check('- zz-mine:' in out and '- zz-hot:' in out, "start: the project's note or the most used note is not in the index")
    check(out.index('- zz-mine:') < out.index('- zz-hot:') < out.index('- note-000:'), 'start: the index is not ordered project, most used, rest')
    check('more notes in that folder' in out and 'the next step' in out, 'start: no line for the notes left out, or the handoff is gone')
    check(out.rstrip().endswith('unless the user asks for detail.'), 'start: the last line was cut')

    # ---- compact.js: instructions for the summary
    out = hook('compact.js', {'trigger': 'auto'}, raw=True)
    check('rule' in out and 'rejected' in out and 'Leave out' in out, 'compact: no instructions for the summary')

    # ---- brief.js: every worker gets the report format, the check command and the decisions
    (d / '.helena').mkdir()
    (d / '.helena' / 'test').write_text('python -m pytest -q tests/fast\n')
    subprocess.run(['git', 'init', '-q'], cwd=d)
    ctx = (hook('brief.js', {'agent_type': 'general-purpose', 'agent_id': 'a1'}).get('hookSpecificOutput') or {}).get('additionalContext', '')
    check('at most 20 lines' in ctx and 'python -m pytest -q tests/fast' in ctx, 'brief: no report format or no check command')
    check('use sqlite, not postgres' in ctx, 'brief: the Decisions section did not reach the worker')
    check(len(ctx) < 2600, f'brief: {len(ctx)} characters for every worker is too much')

    # ---- delegate.js: a long report goes back once, a short one and the second try pass
    stop = lambda said, agent='a1': hook('delegate.js', {'hook_event_name': 'SubagentStop', 'agent_id': agent, 'last_assistant_message': said})
    check(stop('done: src/a.js:10 fixed, tests pass') == {}, 'report: a short report was sent back')
    first = stop('x' * 9000, 'a2')
    check(first.get('decision') == 'block' and 'file' in first.get('reason', ''), 'report: a 9000-character report was not sent back')
    check(stop('x' * 9000, 'a2') == {}, 'report: the same worker was sent back twice')
    (d / '.helena' / 'delegate').write_text('report: off\n')
    check(stop('x' * 9000, 'a3') == {}, 'report: `report: off` was ignored')
    (d / '.helena' / 'delegate').unlink()

    # ---- wave.js: a worktree's changes land uncommitted in the main tree; a patch that collides does not, and stays
    r = tmp / 'repo'
    r.mkdir()
    g = lambda *a, cwd=r: subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *a], cwd=cwd, capture_output=True, text=True)
    g('init', '-q')
    (r / 'a.txt').write_text('one\n')
    (r / 'b.txt').write_text('one\n')
    g('add', '-A'); g('commit', '-qm', 'base')
    w1, w2, w3 = tmp / 'w1', tmp / 'w2', tmp / 'w3'
    for w in (w1, w2, w3):
        g('worktree', 'add', '-q', '-b', w.name, str(w))
    (w1 / 'a.txt').write_text('one\ntwo from w1\n')
    (w1 / 'new.txt').write_text('made by w1\n')
    (w2 / 'b.txt').write_text('one\ntwo from w2\n')
    g('add', '-A', cwd=w2); g('commit', '-qm', 'builder committed', cwd=w2)     # a builder that committed still lands
    (w3 / 'a.txt').write_text('ONE changed by w3\n')                            # collides with w1
    land = subprocess.run(['node', str(ROOT / 'wave.js'), 'land', str(w1), str(w2), str(w3)], cwd=r, capture_output=True, text=True)
    check(land.returncode == 1 and land.stdout.count('landed') == 2 and 'NOT LANDED' in land.stdout, f'wave: wrong result: {land.stdout!r}')
    check((r / 'a.txt').read_text() == 'one\ntwo from w1\n' and (r / 'new.txt').exists() and 'w2' in (r / 'b.txt').read_text(), 'wave: the work did not land')
    check(g('diff', '--cached', '--name-only').stdout.strip() == '' and g('log', '--oneline').stdout.count('\n') == 1, 'wave: something was staged or committed in the main tree')
    check(not w1.exists() and not w2.exists() and w3.exists(), 'wave: landed worktrees were kept, or the collided one was removed')
    check('w1' not in g('branch').stdout and 'w3' in g('branch').stdout, "wave: a landed worktree's branch was kept")
    where = subprocess.run(['node', str(ROOT / 'wave.js'), '--where'], capture_output=True, text=True).stdout
    check('wave.js" land' in where, 'wave: --where does not print the command')

    # ---- gate.js: 20 tool calls in one request on Opus with 150k of context: one line, once; never inside a worker
    tr = d / 'heavy.jsonl'
    rows = [{'type': 'user', 'message': {'content': 'do the big thing'}}]
    for i in range(21):
        rows.append({'type': 'assistant', 'timestamp': '2026-11-11T10:00:00Z', 'message': {'model': 'claude-opus-5-5', 'content': [{'type': 'tool_use', 'id': f'u{i}', 'name': 'Grep', 'input': {'pattern': f'p{i}'}}],
                     'usage': {'input_tokens': 10, 'cache_read_input_tokens': 150000, 'cache_creation_input_tokens': 0}}})
        rows.append({'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': f'u{i}', 'content': f'result {i}'}]}})
    tr.write_text(''.join(json.dumps(r) + chr(10) for r in rows))
    gate = lambda **more: (hook('gate.js', {'hook_event_name': 'PreToolUse', 'tool_name': 'Grep', 'tool_input': {'pattern': 'next'},
                                            'transcript_path': str(tr), 'prompt_id': 'p1', **more}).get('hookSpecificOutput') or {})
    check(gate(agent_id='w1') == {}, 'heavy: a worker was told its calls are expensive')
    first = gate()
    check('helena:builder' in first.get('additionalContext', '') and '150k' in first.get('additionalContext', '') and 'permissionDecision' not in first,
          f'heavy: no line after 20 calls at 150k on Opus: {first!r}')
    check(gate() == {}, 'heavy: the line was said twice in one request')
    tr.write_text(tr.read_text().replace('claude-opus-5-5', 'claude-sonnet-5-5'))
    check(gate(prompt_id='p2') == {}, 'heavy: said on a Sonnet session')

    # ---- trim.js: a file too big to read whole is refused with its outline
    (d / 'huge.py').write_text(chr(10).join(f'def handler_{i}(x):' + chr(10) + '    return x  # ' + 'pad ' * 300 for i in range(120)))
    why = (hook('trim.js', {'tool_name': 'Read', 'tool_input': {'file_path': str(d / 'huge.py')}}).get('hookSpecificOutput') or {}).get('permissionDecisionReason', '')
    check('Outline' in why and 'def handler_0(x):' in why and why.count(chr(10)) <= 45, 'trim: a refused big file came without its outline (or the outline is not capped)')

    # ---- diet.py: lists what a plugin and the user's own agents put in every message, counts uses, --off is per project
    cl = home / '.claude'
    plug = cl / 'plugins' / 'cache' / 'heavy'
    (plug / 'skills' / 'deploy').mkdir(parents=True)
    (plug / 'skills' / 'deploy' / 'SKILL.md').write_text('---\nname: deploy\ndescription: ' + 'deploys things ' * 40 + '\n---\n')
    (cl / 'agents').mkdir()
    (cl / 'agents' / 'idle-agent.md').write_text('---\nname: idle-agent\ndescription: an agent nobody starts, described at enough length to weigh something in every message\n---\n')
    (cl / 'settings.json').write_text(json.dumps({'enabledPlugins': {'heavy@market': True}}))
    (cl / 'plugins' / 'installed_plugins.json').write_text(json.dumps({'plugins': {'heavy@market': [{'installPath': str(plug)}]}}))
    (cl / 'projects' / 'p').mkdir(parents=True)
    (cl / 'projects' / 'p' / 's.jsonl').write_text('{"name":"Skill","input":{"skill":"heavy:deploy"}}\n' * 3)
    diet = lambda *a: subprocess.run([sys.executable, str(ROOT / 'diet.py'), *a], cwd=d, capture_output=True, text=True, encoding='utf-8', env=env).stdout
    out = diet()
    check('plugin heavy: 1 skills' in out and '    3  plugin heavy' in out, f'diet: the plugin or its 3 uses are missing: {out!r}')
    check('never called (1): idle-agent' in out, 'diet: the agent nobody starts is not named')
    check('heavy@market is off in this project' in diet('--off', 'heavy'), 'diet: --off did not answer')
    check(json.loads((d / '.claude' / 'settings.local.json').read_text())['enabledPlugins'] == {'heavy@market': False}, 'diet: --off did not write the project setting')
    check('plugin heavy' not in diet() and json.loads((cl / 'settings.json').read_text())['enabledPlugins']['heavy@market'] is True,
          'diet: a plugin turned off here is still listed, or the user setting was changed')

    # ---- diet.py lint: an npm script restated, a directory tree, a long prohibition list; reported, never changed
    (d / 'package.json').write_text(json.dumps({'scripts': {'build': 'vite build'}}))
    body = ['# App', 'Plain text.', '`npm run build` runs `vite build`.', 'More text.']
    body += ['```', 'app/', '├── src', '│   └── a.js', '├── b.js', '└── c.js', '```', 'Text again.']
    body += [f'- Never do thing {i}' if i % 2 else f'- **Do not** do thing {i}' for i in range(8)] + ['', '- Use tabs']
    (d / 'CLAUDE.md').write_text('\n'.join(body), encoding='utf-8')
    out = diet()
    check('CLAUDE.md: ~' in out and 'tokens could go (paid on every call):' in out, f'diet lint: no block: {out!r}')
    check('lines 3-3: npm script' in out and '(package.json already says it)' in out, 'diet lint: npm script line range')
    check('lines 7-10: directory tree' in out, 'diet lint: tree range')
    check('lines 13-20: prohibition list' in out, 'diet lint: prohibition range')
    (d / 'CLAUDE.md').write_text('# App\nPlain text.\n- Never do this\n- Use tabs\n', encoding='utf-8')
    check('could go' not in diet(), 'diet lint: a clean CLAUDE.md printed a block')

for e in errors:
    print('failed:', e)
print(f'{len(errors)} error(s)' if errors else 'ok')
sys.exit(1 if errors else 0)
