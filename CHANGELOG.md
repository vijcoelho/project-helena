# Changelog

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
