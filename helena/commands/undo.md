---
description: Delete a skill Helena created by herself (she will not create it again); with "learned" drop the last lesson she added to a skill; with "fold" restore a skill from before she folded its lessons in
argument-hint: <skill name> [learned|fold]
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/skills.py" undo $ARGUMENTS`

Tell the user the result in one line. Do not run anything else.
