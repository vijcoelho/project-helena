---
description: Routines Helena runs by herself every so often (read-only, with a spending cap). List, add, remove, or run one now
argument-hint: [what to do and how often | remove <name> | run <name>]
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/routines.py"`

Above are the user's routines. Script: `${CLAUDE_PLUGIN_ROOT}/routines.py`. Request: $ARGUMENTS

- Empty request: show the list as is.
- "remove <name>" or "run <name>": run `python "<script>" remove <name>` (or `run <name>`) and give the result in at most five lines.
- Anything else describes a new routine. Build this JSON and run `python "<script>" add '<json>'`:
  `{"name": "kebab-case", "prompt": "...", "every": "<n>h or <n>d", "max_budget_usd": 0.1, "project": "...", "goal": "..."}`
  - prompt: self-contained instructions in the user's language; the routine runs later with no memory of this chat and can only read files and the web.
  - every: "every Monday" is 7d, "daily" is 1d.
  - max_budget_usd: 0.1 unless the user gave a cap.
  - project: absolute path of the current folder when the routine is about this project; leave it out otherwise.
  - goal: only when the user named something to reach (progress then goes to the project's note in the vault).
  Show the one-line result. Do not run anything else.
