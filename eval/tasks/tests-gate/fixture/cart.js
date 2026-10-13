// Sum of price times quantity, in dollars.
function total(items) {
  return items.reduce((sum, i) => sum + i.price * i.qty, 0);
}

function label(items) {
  return `Total: $${total(items).toFixed(2)}`;
}

module.exports = { total, label };
