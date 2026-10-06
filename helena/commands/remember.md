---
description: Teach Helena something right now (a rule, a preference, a project fact)
argument-hint: <what to remember>
---

Save this to Helena's memory now: $ARGUMENTS

1. The vault path is the single line in `~/.helena/vault` (if missing, use `~/Helena`). Notes live in `<vault>/Memory/`.
2. If a note already covers this, update it (add a `## <today>` section). Otherwise create `<vault>/Memory/<kebab-slug>.md`:
   ```markdown
   ---
   type: rule | preference | fact | user
   description: <one line, used to decide relevance at session start>
   source: remember
   ---
   <the fact, plus the why if the user gave one>
   ```
3. One fact per note. Link related notes with `[[slug]]`. Write in the language the user writes in. Never store secrets.
4. Reply in one line with the note's name.
