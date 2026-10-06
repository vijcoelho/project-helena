---
name: library
description: When a request needs a specialty that is not among the loaded skills (animation, 3D, design systems, security audits, scraping, payments...), check Helena's library and load only what is needed.
---

# Helena's library

Skills that do not load in every session. They live in `~/.helena/library/`.

1. Read `~/.helena/library/CATALOG.md` (name, description and path of every skill).
2. Pick only what the request needs (usually 1 to 3).
3. Read each one's `SKILL.md` and follow it. Relative paths inside a skill start from its own folder.

Nothing in the catalog fits? Say so and carry on without it. Install more with `python library.py install <repo>`.
