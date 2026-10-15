---
name: library
description: A request needs a specialty no loaded skill covers (animation, 3D, security audit, scraping, payments...): load only that skill from the Helena library.
---

# Helena's library

Skills that do not load in every session. They live in `~/.helena/library/`.

1. Read `~/.helena/library/CATALOG.md` (name, description and path of every skill).
2. Pick only what the request needs (usually 1 to 3).
3. Read each one's `SKILL.md` and follow it. Relative paths inside a skill start from its own folder.

Nothing in the catalog fits? Say so and carry on without it. Install more with `python library.py install <repo>`.
