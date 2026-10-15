---
description: Copy one of your memory notes into this repo's .helena/memory for the team
argument-hint: <note>
---

Share the memory note "$ARGUMENTS" with the team of this repository.

1. The vault path is the single line in `~/.helena/vault` (if missing, use `~/Helena`). Find the note in `<vault>/Memory/`
   whose name or description matches; if more than one matches, ask which.
2. Copy it to `<repo root>/.helena/memory/<same-name>.md`. Remove `source:` from the frontmatter and anything personal
   (names of people, local paths outside the repo). Never copy secrets.
3. Do not commit. Tell the user in two lines: the file is ready for review, and once merged every teammate's AI
   (Claude, Codex, any MCP client with Helena) starts every session in this repo knowing it.
