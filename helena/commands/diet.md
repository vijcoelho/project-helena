---
disable-model-invocation: true
description: What sits in the context before you type (plugins, skills, agents, CLAUDE.md) and how often each was used
argument-hint: [days | --off <plugin>]
allowed-tools: Bash(python:*)
---

!`python "${CLAUDE_PLUGIN_ROOT}/diet.py" $ARGUMENTS`

Show this to the user as is. Then, in at most three short lines, name the heaviest pieces that were never called and the
exact command or file that removes each from this project. Turn nothing off unasked. Do not run anything else.
