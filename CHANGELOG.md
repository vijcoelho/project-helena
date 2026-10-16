# Changelog

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
