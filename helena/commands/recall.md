---
description: Search past sessions for what was said or decided about something (no LLM, plain text scan)
argument-hint: <words> [--days N] [--project name]
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/history.py" recall $ARGUMENTS`

Answer the user's question from the hits above in at most five lines, naming the date and the project of each thing you
use. If it says nothing was found, say so plainly and do not guess. Do not run anything else.
