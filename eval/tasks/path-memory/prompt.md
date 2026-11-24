Add an exported `lateFee(balanceCents, rateBps)` function to `src/billing.js` that returns the fee in integer cents for `(balanceCents * rateBps) / 10000` (returning 0 when `balanceCents <= 0`).
