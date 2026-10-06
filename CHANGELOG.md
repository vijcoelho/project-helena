# Changelog

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
