const test = require('node:test'), assert = require('node:assert');
const { total, label } = require('./cart');

const items = [{ price: 12.5, qty: 2 }];

test('total', () => {
  assert.strictEqual(total(items), 25);
  assert.strictEqual(total([]), 0);
});

test('label', () => {
  assert.strictEqual(label(items), 'Total: $25.00');
});
