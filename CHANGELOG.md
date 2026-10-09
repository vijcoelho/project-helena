# Changelog

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
