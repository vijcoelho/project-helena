---
type: rule
description: arredondamento de taxa de fatura sempre para cima
paths: src/billing.js
---
Fee rounding in `src/billing.js` MUST always round UP with `Math.ceil` (never `Math.round` or `Math.floor`), per accounting contract #412.
