---
name: handoff
description: When the user is about to leave or pause ("I have to go", "save everything", "we'll continue later", "leave it for another AI"), or asks to continue ("pick up where you left off"). The handoff always goes in HANDOFF.md at the project root.
---

# Handoff: HANDOFF.md

One file, always this name, at the project root. No `continue-here.md`, `notes/x.md` or loose notes.

## When pausing

Rewrite (do not pile up history) `HANDOFF.md` with exactly these sections:

```markdown
# Handoff
## Done
- what is finished and tested (file:line when it helps)
## Next
- next step first, concrete enough for another AI to start without asking
## How to run
- commands to start/test
## Decisions
- choices made and why (what must not be undone without talking first)
```

## When continuing

Read `HANDOFF.md`, do the first item under **Next**, and update the file at the end.
