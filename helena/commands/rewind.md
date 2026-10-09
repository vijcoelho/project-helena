---
description: Undo what the AI did: put this folder back as it was before the last request (or n requests back)
argument-hint: [n]
allowed-tools: Bash(node:*)
---

!`node "${CLAUDE_PLUGIN_ROOT}/hooks/rewind.js" $ARGUMENTS`

Show this to the user as is. With no number it is the list of snapshots: tell them `/helena:rewind <n>` puts the folder
back to before that request, and that running the same rewind again undoes it. Do not run anything else.
