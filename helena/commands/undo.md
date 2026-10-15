---
description: Delete a skill Helena created; "learned" drops its last lesson, "fold" restores it
argument-hint: <skill name> [learned|fold]
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/skills.py" undo $ARGUMENTS`

Tell the user the result in one line. Do not run anything else.
