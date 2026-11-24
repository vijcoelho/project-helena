// Billing utilities in cents.
export function netSubtotal(subtotalCents, discountCents = 0) {
  return Math.max(0, subtotalCents - discountCents);
}
