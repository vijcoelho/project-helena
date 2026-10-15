---
name: readability
description: Before delivering ANY visual change (site, page, app, dashboard, theme, color): check every text's contrast on the page and fix what is unreadable.
---

# Readability before saying "done"

Don't wait for the user to notice that some text is hard to read.

1. Make the requested change.
2. Run the checker on the page (file or local server):
   ```bash
   node "${CLAUDE_PLUGIN_ROOT}/tools/contrast.mjs" index.html
   node "${CLAUDE_PLUGIN_ROOT}/tools/contrast.mjs" http://localhost:3001
   ```
   If `${CLAUDE_PLUGIN_ROOT}` is not set, the tool is at `helena/tools/contrast.mjs` in the project-helena repo.
3. Fix every listed item, **including outside what was asked**: darken/lighten the text color while keeping the palette
   (same hue, different lightness). Do not redesign.
4. Run again until it prints `contrast OK`. At the end, say which texts you fixed.

The checker cannot measure text over images/gradients: look at a screenshot and, when in doubt, put a dark scrim behind it.
