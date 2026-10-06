---
description: First day with Helena - point her at your Obsidian vault and let her learn from your past sessions, so she does not start empty
argument-hint: [vault path] [number of past sessions, default 10]
allowed-tools: Bash(python:*), Read, Write
---

Request: $ARGUMENTS

1. Read `~/.helena/vault` (one line: the vault path). If it does not exist and the request has no path, ask the user where
   their Obsidian vault is (any folder works; default `~/Helena`). Write the path to `~/.helena/vault` and create the folder if missing.
2. Tell the user in one line: Helena will read their last N project sessions (N from the request, default 10) on Haiku,
   a few cents each, and turn corrections, preferences and decisions into notes.
3. Run in the background: `python "${CLAUDE_PLUGIN_ROOT}/distill.py" --backfill N`
4. When it finishes, list the notes it created in `<vault>/Memory/` (names only) and say they load from the next session on.
   Wrong ones go away with /helena:forget.
