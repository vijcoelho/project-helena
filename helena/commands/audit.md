---
description: What Helena's hooks blocked or asked about (secrets, packages, destructive commands, tests, team policy)
argument-hint: [days] [--json]
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/audit.py" $ARGUMENTS`

Show this report to the user as is. With --json it is the raw log for a team's own tools. Do not run anything else.
