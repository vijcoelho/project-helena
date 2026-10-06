---
description: Delete a skill Helena created by herself (she will not create it again)
argument-hint: <skill name>
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/skills.py" undo $ARGUMENTS`

Tell the user the result in one line. Do not run anything else.
