---
description: Show what Helena has learned so far (memories, kits, library, skill candidates)
---

Show the user what their Helena knows. Read only, change nothing.

- Vault: the line in `~/.helena/vault` (default `~/Helena`).
- **Memories**: count the notes in `<vault>/Memory/` and list each name with its `description:` line.
- **Kits**: the keys of `~/.helena/kits.json` and their `trigger` (none yet is normal on a fresh install).
- **Library**: how many skills are in `~/.helena/library/CATALOG.md`.
- **Skill candidates**: the notes in `<vault>/Inbox/` waiting for a benchmark (`python eval/promote.py <name>`).

Plain short lists. If everything is empty, say that Helena starts blank and learns as they work with her.
