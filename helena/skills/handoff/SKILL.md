---
name: handoff
description: User is leaving or pausing ("I have to go", "save everything", "continue later") or asks to pick up where they left off. Always HANDOFF.md at the project root.
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
- what was considered and rejected, and why (so the next AI does not try it again)
```

## When continuing

Read `HANDOFF.md`, do the first item under **Next**, and update the file at the end.
