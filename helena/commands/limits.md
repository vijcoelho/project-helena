---
description: How much of each AI plan is gone (5 hours and week), and whether the week lasts at this pace
allowed-tools: Bash(node:*)
---

!`node "${CLAUDE_PLUGIN_ROOT}/hooks/limits.js"`

Show this to the user as is. If one AI runs out before its reset and another has room, say in one line which one to
continue in; the command is `<cli> "Read HANDOFF.md and continue from Next"` in this folder. Do not run anything else.
