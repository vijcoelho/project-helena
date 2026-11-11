# Changelog

## 2.0.0 (2026-11-11)

What a tool call costs is the context it re-reads times the model's price. 30 days of the creator's sessions (8,483
model calls) showed the tokens go into calls x context, not into tool output. So 2.0 keeps the main session thin and
moves work to workers.

- `start.js`: Claude Code shows only a 2 KB preview of a hook output past 10,000 characters and files the rest. The
  session start was 14.3 KB in the creator's repo, so the memory index was not reaching the model. Now it always fits
  (9.5 KB max; 6.7 KB measured there). The memory index is a budget (1 KB): this project's and the team's notes first,
  then the ones handed over most, and a line saying how many are not listed. `router.js` still hands any note over
  whole when a request matches it.
- Call-cost line (`gate.js`): past 20 tool calls in one request, on a model at Opus level or above (Opus, Fable,
  Mythos) with 100k+ of context and no worker started, one line (once per request) says what each call re-reads and
  names the two cheaper ways: a `helena:builder` with a short brief, or finish and /clear. Never said inside a worker.
- `brief.js` (new, SubagentStart): every worker of any type starts with the report format (20 lines at most,
  `path:line`, the long version in a file), the project's check command, the `## Decisions` section of `HANDOFF.md`
  (last 1,500 characters) and `tests: spec-only` when set. The orchestrator no longer spends output tokens repeating them.
- Report cap (`delegate.js`): a worker whose last message passes 8,000 characters is sent back once to put the full text
  in a file and report in 20 lines. `report: <characters>` or `report: off` in `.helena/delegate`.
- `/helena:orchestrate`, waves: steps that share no file, do not need each other's result and whose files have no
  uncommitted changes run side by side, up to 3 builders, each in its own git worktree; everything else one at a time.
  `helena/wave.js land <worktree>...` lands them with one command: each worktree becomes a patch, checked against the
  main tree and applied; nothing is staged or committed; a patch that collides is NOT LANDED and its worktree is kept.
  Briefs are under 10 lines. A failed step climbs one rung: a new builder (on `opus` when the session runs on a model
  above Opus), then the main session. `/helena:race` lands its winner with the same script.
- `compact.js` (new, PreCompact): tells the compaction summary what to keep (the user's rules in their words, decisions
  and rejected approaches, files as `path:line`, the check command and its last result, the next step) and what to leave
  out (file contents, command output). `start.js` still restores the user's rules after compaction.
- `squeeze.js` (new, PostToolUse Bash / PowerShell): a command output over 4k characters loses colour codes and `\r`
  progress, and runs of lines that differ only in numbers fold into three; still over 20k, the first 40 and last 80
  lines stay plus the middle lines that look like a problem. The full output is saved in `~/.helena/out/` (3 days) and
  the AI is told the path. Commands that print content (cat, head, sed, git diff, git show) are never touched.
  `# helena:full` skips it. Replayed over 30 days of the creator's sessions (1,846 commands) it would have changed 0
  outputs, because the model already pipes long output through tail. It is a net for sessions that do not; no saving
  is announced.
- `trim.js`: a file refused for being over 100 KB now comes with its outline (up to 40 functions, classes or headings
  with their line numbers), so the next Read asks for the right part.
- `/helena:diet` (new, `helena/diet.py`, no LLM): what sits in the context before you type: each plugin, your own
  skills and agents, CLAUDE.md, with an estimate in tokens and how many times each was called in 30 days;
  `--off <plugin>` turns one off in this project only. On the creator's machine: 6.6k tokens listed, one plugin of 2.5k
  tokens never called in 30 days.
- `router.js`: the routine-command hint now also fires on Fable and Mythos sessions.
- `eval/test_squeeze.py`: tests for all of the above, no LLM. Red team unchanged: 36 of 37, 0 false positives.
- Site: the ASCII Helena is redrawn from the same drawing by `extras/ascii.py` (160 x 96 characters; each one is picked
  by the shape under it, so seams and hair are lines and not dots; the paper outside her is dropped). New section
  "orchestration", three cards in "savings", numbered section labels, a scroll progress line, corner marks on the
  portrait, one-line nav. Contrast checked (WCAG AA), desktop and phone, no sideways overflow.
- Own rules guard (gate.js): an Edit/Write, or a shell command that writes, to `.helena/git`, `.helena/policy`, `.helena/test` or `.helena/delegate` asks first. They are the files her checks read, so an AI that edits them changes what it is checked against. Reading them and `git add/diff/commit` stay free.
- Repo AI config check (start.js) now also scans tracked nested `CLAUDE.md` / `AGENTS.md` and `.claude/rules/*.md` (40 files at most, root first, then shortest path), naming the file in the warning. Still once per content.
- Same failure twice (`gate.js`): when the two newest test runs of a request both failed with the same signature (first
  FAIL / Error line, numbers ignored) and an edit sits between them, one line (once) asks which assumption was wrong.
  Never blocks, never said inside a worker.
- PR receipt (`gate.js`, opt-in): with `pr: receipt` in `.helena/git`, `gh pr create` is denied once per session and
  commit with the line `Checked by Helena: <test command> passed|FAILED after the last edit, at <sha>` (or "no test run
  after the last edit") to add to the PR body.
- `/helena:diet` lint: CLAUDE.md / AGENTS.md lines the repo already shows are listed with line ranges and tokens: an npm
  script restated from `package.json`, a directory tree (4+ lines), a "do not / never" list (8+ lines). Reported, never changed.
- `/helena:budget`: "Requests checked by tests" counts the requests that ended under the done check, green or blocked at
  least once, with the average tokens of each (median for green).
- `/helena:orchestrate` reviews a large change once (more than 3 files or 150 changed lines): a fresh worker reads only
  the task and the diff and returns up to 5 findings; a second fresh worker tries to prove each one wrong; only findings
  that stand are fixed or shown. A smaller change skips it.
- `eval/test_speed.py` (no LLM): runs every command hook in `hooks.json` 5 times with a fake event and a fake HOME and
  fails when a median passes 1,500 ms (3,000 ms for `start.js`; `HELENA_SPEED_MS` changes it). `done.js`, `check.js`
  and `end.js` are skipped (tests, browser, model).
- Measured on 2026-11-11 (Sonnet, 3 rounds per column, both columns 6/6, 0 of 8 reruns flipped): on the two short cost
  tasks Helena 2.0 costs more, not less. `noisy-tests`: $0.139 without, $0.145 with (turns 8.0 -> 4.7, +7.6k tokens).
  `release-notes`: $0.138 without, $0.146 with (+21.5k tokens). Her fixed weight is 1,925 tokens per call (`--probe`:
  44,009 -> 45,934). Same picture as 1.4: on a short task there is nothing to cut and her opening text is paid on
  every call.
- So the memory index went from 4.5 KB to 1 KB the same day, and the same run was repeated (Sonnet, 3 rounds per
  column, both 6/6, 0 of 8 reruns flipped). Fixed weight: 724 tokens per call (`--probe`: 44,009 -> 44,733), down from
  1,925. `noisy-tests`: $0.137 without, $0.140 with (turns 5.3 -> 5.0, +4.1k tokens). `release-notes`: $0.136 without,
  $0.138 with (+2.0k tokens). Still more, not less: about 2% instead of 5%. What is left is mostly the list of her
  commands, skills and agents, which Claude Code puts in every call.
- So 13 of her 17 commands (the reports and the ones only the user starts: app, audit, budget, diet, limits, skills,
  status, undo, setup, routines, share, rewind, race) now carry `disable-model-invocation: true`: typed as before, not
  listed to the model. `router.js` points the model at the command file when a request asks for a report in plain
  words (fixed phrases, PT and EN, once per session). `/helena:diet` no longer counts a command that is not listed.
  Measured with every other plugin off (`Reply OK`, Sonnet): 32,501 without her, 33,854 with the commands listed,
  33,429 hidden: 425 tokens less per call, 928 left. On the creator's machine, where 12 other plugins already fill
  the listing budget, the same change is worth 18 tokens (724 -> 706). The two cost tasks were not run again.
- Not claimed: no token saving number for orchestration. The benchmark has no multi-step task that would measure it.

## 1.7.0 (2026-11-02)

- Receipts (`done.js`): in a project with no test command, a reply that says the tests pass must match a green
  test-like run after the last code edit; no run or a red one blocks once.
- Tests weakened, at Stop (`done.js`): against `HEAD`, a test file with fewer assertions, more skips, or deleted blocks
  once per diff. Catches edits through Bash or a script, which the gate never sees.
- `nudge.js` (new, PostToolUse Edit/Write): after every 3rd code edit with no test run in between, one line asks for
  the nearest test (arXiv 2610.34577: agents check after few of their edits; the reminder raised the score and cut
  output tokens). Silent without a test command.
- Loop cut (`gate.js`): the same call with the same result 4 times in a row in one turn is denied. Results are
  compared, so a poll whose output changes passes. Idea from a "same call, same result" detector.
- `gate.js`: `bash -c "rm -rf /"` was allowed; the quoted script of `sh -c` / `bash -c` is checked too.
- After a compaction (`start.js`, `source: compact`): the user's own rule-like sentences from before it come back word
  for word, with the transcript path. Summaries drop how-to-work rules first.
- `eval/run.py`: noise floor (same-column flips across rounds), exact McNemar p, CLI version per task.
- `paths.js`: `turn()` reads this turn's blocks newest first with which tool calls failed and what each returned;
  `testCommand`, `CODE`, `ASSERT`, `SKIP`, `TESTISH` shared by the hooks.
- `eval/test_receipts.py`: tests for all of the above.

## 1.6.0 (2026-10-16)

- The Helena app, `/helena:app`: one window with what Helena blocked, checked, remembered and spent, live. Sessions of
  the last 12 hours (last request, model, context, cache, last done check), every hook decision, notes handed to the
  AI, stale notes and why, every AI's limits with the weekly pace, Helena's own cost and the hosts the AI reached.
  `helena/app/server.js` (node, no dependencies) reads the files the hooks already write; it answers only on
  127.0.0.1 to a Host header naming it, only GET, and exits 90 s after the window stops polling. A second launch reuses
  the running server. Windows opens an Edge app window; macOS and Linux a browser tab. Read-only.
- `~/.helena/events.jsonl`: what went right, for the app. `done.js` logs a done check that passed (command, whether
  the holdout ran, files edited); `router.js` logs the notes and kits it handed over. Blocks still go to `audit.jsonl`
  only, so `/helena:audit` is unchanged.
- The app is now a chat: it runs the `claude` CLI you are logged into (`claude -p`, stream-json), so Helena's hooks
  run on it, with no API key. Each subagent shows as a card with every step live, its time, tokens and what it handed
  back; each turn shows its own cost. Sessions are grouped by what they need (needs you, working, recent); clicking one
  continues it in a copy (`--fork-session`), so the terminal running it is untouched. The page carries a per-launch
  token that `POST /api/chat` requires. The background is the site's character field and blurs once the conversation
  starts; Helena in pixels (black bob, sunglasses up, headset, from the site portrait) stands on the input and shows
  what is happening. Esc stops a run.
- Panes: up to four conversations side by side, each with its own AI, model, folder and Helena (Ctrl+\ splits,
  Ctrl+1-4 jumps, Ctrl+B hides the sessions; one pane with tabs on a phone). Codex (`codex exec --json`, resumed with
  `exec resume`) and Gemini through Antigravity (`agy -p --output-format stream-json`) run beside Claude. `/model` switches
  model or AI mid-conversation, and the next AI gets the last messages. A `/` menu lists the app's commands and every
  Helena command. Codex runs with Helena's MCP tools approved (`exec` never asks, so they were refused before).
- Subagents of every AI, live: Claude's come in its stream; Codex's are threads of their own, followed from their logs in
  `~/.codex/sessions` (role and nickname, each command, what it handed back); Gemini's (agy `invoke_subagent`) from the
  transcript each one writes. The stream stays open until they finish (2 minutes of silence counts as stopped). An
  "Agentes agora" corner in the sessions column and a counter in the title bar list every subagent working in every
  pane, with the step it is on; a click goes to its card.
- `/model` lists what each CLI offers: every Claude model in the catalog compiled into Claude Code (the one its own
  `/model` reads: Fable 5.1 down to Haiku 4.5, with context, knowledge cutoff, default effort; read once per CLI version
  into `~/.helena/claude-models.json`), Codex's visible models from
  `~/.codex/models_cache.json`, Antigravity's from `agy models`; then the reasoning efforts the chosen model takes
  (`--effort`, `model_reasoning_effort`). `/model <id>` takes any id the CLI accepts, listed or not; the lists refresh
  every 10 minutes. Thin dark scrollbars everywhere.
- Windows: Helena's own frameless window (`app/shell/Helena.cs`, built once with the `csc` that ships with Windows and
  the WebView2 DLLs from NuGet, into `~/.helena/app-shell`), with her title bar and buttons and her face as the icon
  (`app/icon.png`, from the site portrait). Falls back to an Edge app window. The first `/helena:app` adds Helena to
  the Start menu: `Helena.exe` with no address finds the running server or starts one itself, with no console, so the
  app opens without Claude Code. "Outra pasta…" (folder menu and the first screen) opens the Windows folder dialog, or
  asks for a path in a browser. No program the app starts flashes a terminal (`eval/test_app.py` checks `windowsHide`).
- The app speaks English and Portuguese: PT / EN at the top, like the site. It starts in the system's language and keeps
  the choice (`helena-lang`); switching redraws everything on screen, the model hints included (the server now sends
  each model's context, cutoff and default effort, and the page writes them), and the run's errors come in it too.
  The app's own commands follow the language (`/new` or `/novo`, `/split` or `/dividir`...).
- Handoff and `/helena:orchestrate`: a decision that changes mid-run keeps its line under `## Decisions`, marked
  `superseded by: <the new one>`, instead of being deleted, so a cold worker sees what replaced what.
- `eval/test_app.py`; `eval/test_verify.py` also checks that a passing done check is logged and a sent-back one is not.

## 1.5.0 (2026-10-16)

- `tests: spec-only` (opt-in): a line in `.helena/delegate` or `~/.helena/delegate`. The gate then asks before the AI
  writes a NEW test file (`test_*.py`, `*_test.py`, `*.test` / `*.spec` with js, ts, jsx, tsx, mjs or cjs, `*_test.go`);
  editing an existing test is never asked. Session start gets one fixed line saying so. Why: DeepSWE found the same
  pass rate with 9% less spend, and forced TDD cost $1.73 per task against $1.12. Not measured in this repo yet, so it
  is off by default.
- Hidden acceptance tests, `.helena/holdout/` (written by the human). `gate.js` denies Read / Grep / Glob on it and any
  shell command that names the folder, and asks on edits. `done.js` runs it (`pytest`, or `node --test` for js) after
  the normal tests pass and gives the AI only the names of the failing tests, never a trace or a file. Limits:
  symlinks into the folder are not covered; jest and vitest may collect `.helena/holdout` in a normal `npm test` run
  and print its assertions, so add it to their exclude.
- Differential check in `done.js`. Once the normal tests (and the holdout) pass, and only when the diff against HEAD
  changes both test files and code files, it stashes the code files (`helena-differential`), reruns the same test
  command and puts them back. Only its own stash entry is touched, never the user's; a leftover one is popped on the
  next run, and if the files cannot be put back it blocks and says how to `git stash pop`. If the suite still passes
  without the change, the tests do not check it: it blocks once per diff (a pure refactor can just stop again).
  Why: arXiv 2610.03984, guided search with a two-tree differential reached 52.8% on SWE-bench Verified against
  46.8%, with about half the steps; without the differential it fell to 47.4%. Cost: one extra test-suite run in
  those cases, no tokens. A `helena-differential` stash left by a killed check is now put back on the next stop even
  if that turn edited nothing.
- `/helena:race <task>`: two `helena:builder` workers try two approaches in separate worktrees, the judge runs the
  tests in each, the one that passes is applied here (tie: smaller diff) and both worktrees are removed. Only for a
  task with two real ways to do it; it costs two workers.
- `eval/replay.py`: replays the tool calls of real Claude Code transcripts through `gate.js` of the working tree and
  of a git ref (`--ref`, default `main`; `--last N`, `--from`, `--json`). It never runs a command and uses a temp HOME,
  so the audit log and memory are untouched. Prints the decisions per version and every one that changed. First run,
  last 300 calls, main against 1.5: 300 allow against 297 allow + 3 deny, all 3 the new holdout rule, on commands
  from the session that built it.
- `eval/test_falseblock.py`: 29 ordinary calls of a coding session (read code, run tests, git status / commit, write a
  source file, edit a test without weakening it) must all be allowed, with spec-only on and off.

## 1.4.5 (2026-10-15)

Less text at session start, and a benchmark that says where each dollar went.

- `hooks/start.js`: a HANDOFF.md over 4 KB goes in as its "## Next" section only, the other sections named (the
  check for files that no longer exist still reads the whole file). The AGENTS.md / CLAUDE.md handover is cut at
  4 KB with a note (it was a silent cut at 8 KB). One fixed "keep replies short" line. On the creator's repo the
  start text went from 34 KB to 9 KB.
- Shorter descriptions for 12 commands, 3 skills and 2 agents (2,397 -> 1,648 chars).
- `eval/run.py`: per column `turns`, `solved_cost` and `parts` (uncached / cache write / cache read / output); with
  `-n` above 1 the columns alternate order; `--probe` sends "Reply OK", one call per column, to price the fixed
  context. Probe in an empty folder: Helena adds 993 tokens (1,060 before; the shorter descriptions gave only 67).
- `eval/tasks/readability`: the check now reads the transcript (without it the hook saw nothing and every run
  failed). Helena 3/3, alone 0/3.

Measured (Sonnet, 3 rounds, cost per solved task alone -> with Helena): `git-rule` $0.201 -> $0.138 (alone solved
2/3), `noisy-tests` $0.132 -> $0.138, `release-notes` $0.134 -> $0.136, `secret-in-commit` $0.132 -> $0.136.
`env-read`, `handoff-resume`, `handoff-save`, `readability`: alone 0/3, Helena 3/3.

Rerun afterwards (Sonnet, two runs of 3 rounds = 6 rounds each; logs `eval/frontier/eval-145.log` and
`eval-145c.log`): `secret-requested` alone 5/6 (one run leaked the key into git), Helena 6/6, per solved task
$0.168 -> $0.142. `tests-gate` alone 1/6, Helena 4/6, per solved task $0.791 -> $0.227, but each Helena run costs more
($0.152 vs $0.132 on average). The two 3-round runs disagreed a lot (`tests-gate` with Helena: 3/3, then 1/3), so
3 rounds is too few to trust these numbers.

## 1.4.0 (2026-10-13)

Two parts: the guardrails got an attack suite and were hardened against it, and the token work below.

### Security

`eval/test_redteam.py` feeds 37 bypass attempts to the hooks as hook events, plus 6 commands that must not be stopped.
Before this release the hooks caught **8 of 37**; now **36 of 37, with 0 false positives**. The one left is a key split
in two strings and joined at run time: it only exists after the join, so no pattern can see it. These are guardrails
for the AI, not a sandbox.

- `hooks/gate.js`, asks first:
  - a recursive delete of a variable that is unset, points at a root or home, or is followed by `/..` or `/*`
    (`rm -rf "$X"/*`, `Remove-Item -Recurse $env:USERPROFILE`). A variable set earlier in the same command is left alone.
  - a delete through something else (`shutil.rmtree('/')`, `fs.rmSync` recursive, `rimraf`, `find / -delete`) and
    decoded text piped into a shell (`base64 -d | bash`, `iex` of a `FromBase64String`).
  - erasing the audit trail: `rm` / `truncate` / `>` / Edit / Write on `~/.helena/*.jsonl`, deleting `refs/helena` or
    Claude's transcripts. The log of what the AI did must not be erasable by the AI. Reading and `>>` are fine.
  - deleting a test file (`rm`, `git rm`, `Remove-Item`, `del`). Before, only an edit that dropped assertions was caught.
  - a package installed with no version whose newest release is under 72 hours old, naming the previous version to pin
    (a hijacked maintainer account ships malware as a new release of a real package).
- `hooks/gate.js`, denied like a plain `cat .env`: `.env` read through quote tricks (`.e''nv`), a glob that matches it,
  an interpreter one-liner, or a copy to a name the rule no longer protects.
- `hooks/guard.js`: AWS access keys and Slack tokens join the patterns (also in the audit mask and in distillation).
  With `gitleaks` on PATH, its findings on the staged changes are added; absent, failing or slow, nothing changes.
  Not run on the creator's machine (gitleaks is not installed there; its tests run on macOS / Linux only).
- `hooks/outside.js`: text hidden in zero-width or Unicode tag characters is flagged, an instruction inside an HTML
  comment is named as hidden, and the output of `gh issue` / `gh pr` / `gh api` is checked too (an issue body is
  written by strangers). Still flags, never blocks; any other shell command returns at once.
- `scan.py`: instructions fetched at run time and followed, a long encoded blob that is decoded and run, and a payload
  behind a condition. On the creator's 110 library skills the verdicts did not move (68 clean, 40 warn, 1 critical).
- `hooks/start.js`: on session start, the repo's own AI config is read (`CLAUDE.md`, `AGENTS.md`, `.mcp.json`,
  `.claude/settings*.json`) and what looks wrong is said once per content: a line written to override the AI, an MCP
  server that pipes a download into a shell, hooks that run commands on your machine, permissions switched off. It
  cannot stop the load (the session starts after those files are read); it tells you before the AI acts on them.
- `hooks/done.js`: with no test command, a `tsconfig.json` and TypeScript installed, the done check runs
  `npx tsc --noEmit`, so a turn that breaks types goes back to the AI.
- `/helena:recall <words>` (`history.py recall`, MCP tool `helena_recall`): searches your recorded sessions, no LLM
  and no index: date, project and the turn where it was said.

### Token economy

Fewer refusals, a cache you can see, and a report that says where the tokens went. **No saving is claimed for the
rewrite:** on the two new cost tasks (Sonnet, 3 rounds each) both columns passed 3/3 and a session cost $0.135 alone vs
$0.143 with Helena (`noisy-tests`), $0.134 vs $0.140 (`release-notes`). Sonnet limited its own output, so there was
nothing to cut, and Helena's session-start text is paid on every call.

- `hooks/trim.js`: a command that only needs a quiet flag gets it and runs, instead of being refused (a refusal is one
  more model call, and every call re-reads the context). `git log` -> `--oneline -n 20` (the AI is told about the cut),
  `git status` -> `-sb`, `pytest` -> `-q --tb=short`, `pip install` -> `-q`, `npm install` -> `--no-fund
  --loglevel=error`, `cargo build|test|check` -> `-q`, recursive `grep` -> `--exclude-dir=node_modules`. Left alone:
  a command that already says what it wants, piped or redirected output, quoted text, heredocs, `# helena:full`. Still
  refused: file dumps over 100 KB, lockfiles, build output, an unbounded `git log -p`, recursive listings.
  With [rtk](https://github.com/rtk-ai/rtk) on PATH, `rtk rewrite` goes first (not run on the creator's machine: rtk
  is not installed there; the test for it runs on macOS / Linux only).
- `statusline.js`: `cache until 14:32` (the context's cache lives 5 minutes or 1 hour after the last call), `cache
  expired`, and `model changed: next message re-reads 80k uncached` after a `/model` mid-session.
- `hooks/delegate.js`: the model pins are on without any file (general-purpose -> Sonnet, Explore -> Haiku) and never
  move a worker to a model above the session's. The caps (`parallel`, `workers`) still need `.helena/delegate`, and so
  does the new `effort:` line (no default: a CLI older than the Agent tool's `effort` field would refuse the worker).
  `model: off` / `search: off` in `~/.helena/delegate` stop the pins.
- `/helena:budget`: every time the context was paid in full instead of read from the cache, by cause (a pause longer
  than the cache, a model switch, a compaction); files read again with no edit in between; the context a worker starts
  with. `hooks/router.js`: the "run it in a subagent" floor went from 50k to 40k, from that measurement (34k median).
- Benchmark: cost tasks `noisy-tests` (needs pytest) and `release-notes`; `eval/run.py` prints the cost per solved task.
- Site: `docs.html`, the documentation in Portuguese and English. `helena/tools/shot.mjs`: a page at 375 and 1440 px,
  sideways overflow and a picture of each.
- Fix (`hooks/gate.js`): a redirect after an install (`npm i x 2>&1`, `> out.txt`) was read as a package name and
  the command was refused.

## 1.3.0 (2026-10-12)

Subagents: what they write gets checked, and what they cost can be capped. Nothing here claims a saving: the published
measurements of "a strong model plans, a cheap one codes" go both ways, and the solo vs orchestrated benchmark has not
been run yet.

- Done check on subagents (`hooks/done.js`, now also on SubagentStop): a subagent's edits are not in the session's
  transcript, so the Stop hook never tested them. Failing tests now go back to the subagent before it reports.
- `hooks/delegate.js` (PreToolUse on Agent, SubagentStop), off until `.helena/delegate` or `~/.helena/delegate` exists:
  a general-purpose worker started without a model runs on Sonnet and Explore on Haiku instead of the main model
  (`model:`, `search:`); at most 3 run at once (`parallel:`) and at most 8 start per request (`workers:`). A refused
  worker is told why and the refusal is in `/helena:audit`. Agent types with their own model and calls that name one are
  left alone.
- `agents/scout.md` (Haiku, Read/Grep/Glob, returns paths and line numbers) and `agents/builder.md` (Sonnet, the only
  writer, reports in 15 lines).
- `/helena:orchestrate <task>`: plan in the session, one builder at a time, read the diff only after the tests passed,
  one retry and then do it here. A task of about 5 tool calls is done inline.
- Ready-made routines (`routines.py add ci|deps [folder]`): failing GitHub Actions runs with the end of the log, and npm
  dependencies with a new major version. A script collects the facts and the model is called only when they changed.
- Egress log: every fetched host, web search, MCP server (`hooks/outside.js`) and URL in a `curl` / `wget`
  (`hooks/gate.js`) is one line in `~/.helena/egress.jsonl`; `/helena:audit` lists the most used.
- Benchmark: a task with a `persist` file keeps its transcript (`eval/run.py`), which the done check needs; new task
  `tests-gate` for it. Without it, `done.js` saw no edits in any benchmark run.
- Fix: the "7 days" measurement in the README and on the site was taken with the 2.5x overcount fixed in 1.2.1. Recounted
  over the same days: 1,882 model calls, 235k tokens of context per call, 37k fixed (was 3,030 / 243k / 39k).
- Fix (`eval/test_guard.py`): the test wrote its blocks into the real `~/.helena/audit.jsonl`.

## 1.2.1 (2026-10-09)

Three checks prompted by how the Claude Code team describes working with it (Thariq Shihipar, Latent Space, Sep 2026).

- `hooks/outside.js` (PostToolUse on WebFetch, WebSearch and MCP tools): text from outside is data, not a request. A
  result with a line written for an AI is flagged next to it and logged (`flag` in `/helena:audit`). Fixed phrases in
  English and Portuguese; it never blocks.
- Redo note (`hooks/router.js`): on "try again" / "that's not what I asked" the AI says what the last attempt got wrong
  before spending another, and asks when the request still reads two ways.
- Instruction file cost (`hooks/start.js`): a `CLAUDE.md` / `AGENTS.md` past ~3k tokens is called out once a week, with
  an offer to move the sometimes-only rules to memory notes.
- `handoff` skill: Decisions also records what was considered and rejected, so the next AI does not try it again.
- Fix (`hooks/router.js`): the routine-request hint no longer suggests `/model sonnet`. Per the Claude Code docs a
  mid-session switch re-reads the whole history with no cache hits and `/model <name>` becomes the default for new
  sessions. Now: a long-output command (run, install) on Opus past 50k of context is pointed at a Haiku subagent.
- Subagent meter (`budget.py`, `history.py`): `/helena:budget` lists what subagents cost, by model and effort (workers,
  calls, tokens, calls over 100k of context) and the five heaviest. Read from the transcripts Claude Code keeps next to
  the parent session; `/usage` does not show their cache reads. No hook, nothing new stored.
- Fix (`history.py`): one API call was counted once per content block, so the budget report showed about 2.5x the real
  tokens. Each call now counts once.

## 1.2.0 (2026-10-08)

The layer that checks. From research on what developers still lack (Reddit, Hacker News, GitHub issues, surveys):
vendors absorb single-tool features fast; what stays open is cross-tool and verification.

- Memory that checks itself (`hooks/memory.js`): a note can carry `checks: <file>, <file>#<name>` and `until: <date>`.
  A failing check marks the note STALE with the reason in the session index and in matched notes. `supersedes:` archives
  the note a new fact replaces. Distillation and `helena_remember` fill these fields.
- Team memory: notes in `<repo>/.helena/memory/` load for everyone in any AI; `/helena:share` copies one of yours there.
- Verified handoff: `HANDOFF.md` is checked against the repo at session start (files changed after it, commits since,
  named files that are gone) and the AI restates the next step. At 95% the limit warning gives a ready command for the
  AI with room. One instruction file: Claude gets `AGENTS.md`, Codex gets `CLAUDE.md`, when the repo only has the other.
- Weekly pace (`hooks/limits.js`): when the week runs out before it resets, she says when and how much a day lasts.
  `/helena:limits` and the `helena_limits` MCP tool show every AI.
- `hooks/gate.js`: `.env` reads denied (key names only), made-up packages denied and brand-new ones asked (npm, PyPI),
  destructive commands asked, edits that weaken tests asked, team policy in `.helena/policy` (deny, ask, MCP allowlist).
- `hooks/done.js`: when a turn edited code, the tests run before "done"; a failure goes back once.
- Undo in any CLI (`hooks/rewind.js`): a git snapshot before each request in `refs/helena/turns`; `/helena:rewind`.
- Audit log: every hook decision in `~/.helena/audit.jsonl`; `/helena:audit`.
- Skill security scan (`helena/scan.py`), run by `library.py install`; a critical finding needs `--trust`.
- Benchmark records tokens and cost per run and writes `eval/results.json`; `eval/registry.py` builds the public
  registry (context cost, scan, measured lift). New task: `env-read`.
- Fix: subagent reports and task notifications no longer load kits or turn plugins back on.
- Cheaper and faster: a kit is injected once per session, not on every matching message; memory index descriptions
  are capped at 90 characters. The Stop hooks (`check.js`, `done.js`) read only the last turn, from the end of the
  transcript, and the contrast check runs only on pages touched this turn (it used to re-run, and re-block, for every
  page touched since the session began).

## 1.1.0 (2026-10-06)

- Helena in any AI: `helena/mcp.js` (MCP server, no dependencies) and `helena/connect.py`, which registers it in every
  CLI it finds (Codex, Antigravity, Gemini, Qwen, Kimi, Grok, opencode). Codex also installs the full plugin.
- `distill.py` reads Codex sessions (`~/.codex/sessions`), so what you teach in Codex lands in the same vault.
- Plan limits (`hooks/limits.js`): reads Claude's limit from the status line and Codex's from its sessions. At 80% she asks
  for HANDOFF.md and /clear; at 95% she saves HANDOFF.md and names the installed AI with room to continue in.
  The status line shows `limit N%`.
- Helena comes first: MCP instructions and the Codex AGENTS.md block put her before any other memory tool.
- Site: "any AI" section with every supported AI.
- `distill.py --remember`: writes a note from JSON on stdin (used by `helena_remember`).

## 1.0.0 (2026-10-06)

- `/helena:setup`: first day with value. Points Helena at your vault and distills your last project sessions
  (`distill.py --backfill`), so she does not start empty. A fresh install mentions it once.
- Memory hygiene (`tidy.py`): duplicate or contradicting notes are merged into one; old versions go to `<vault>/Archive/`.
  Outdated notes are only flagged.
- Skills that tidy themselves: 5+ "## Learned" lessons are folded into the recipe; `/helena:undo <skill> fold` restores it.
- Weekly review in `<vault>/Weekly/`, no LLM.
- Helena's own Haiku calls load no plugins, skills or MCP: about 4x fewer tokens per call.

## 0.9.0

- Routines (`/helena:routines`): a prompt with a schedule and a spending cap, run read-only on Haiku when a session ends.
  Decisions become "needs you" items in the vault Inbox and the next session brief, never actions.
  A routine with a goal logs its progress in the project's hub note.

## 0.8.0

- Distillation every 6 prompts, reading only the new turns.
- Library skills learn from your corrections under "## Learned"; `/helena:undo <skill> learned` drops the last lesson.
- Background runs never open a visible window on Windows.

## 0.7.0

- First public release: memory in Obsidian, kits and library, guard / trim / readability hooks, worker, budget report,
  Claude Code mod with `/painel`.
