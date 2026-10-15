---
description: Where your tokens went this week, what subagents cost, and Helena's own cost
argument-hint: [days]
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/budget.py" $ARGUMENTS`

Show this report to the user as is. Then, in at most three short lines, point out the single biggest thing they can do to
spend less (usually: long sessions; start fresh with /clear after saving HANDOFF.md). Do not run anything else.
