"""Totals for real orders, checked by hand against the price list when each rule went in."""
import pytest

import pricing

# unit price in cents, quantity, country, coupon, total in cents
CASES = [
    (1990, 1, 'BR', None, 2328),
    (1990, 1, 'BR', 'WELCOME', 1743),
    (1990, 1, 'BR', 'VIP', 573),
    (1990, 1, 'US', None, 2149),
    (1990, 1, 'US', 'WELCOME', 1609),
    (1990, 1, 'US', 'VIP', 529),
    (1990, 1, 'PT', None, 2448),
    (1990, 1, 'PT', 'WELCOME', 1833),
    (1990, 1, 'PT', 'VIP', 603),
    (450, 5, 'BR', None, 2632),
    (450, 5, 'BR', 'WELCOME', 2047),
    (450, 5, 'BR', 'VIP', 878),
    (450, 5, 'US', None, 2430),
    (450, 5, 'US', 'WELCOME', 1890),
    (450, 5, 'US', 'VIP', 810),
    (450, 5, 'PT', None, 2768),
    (450, 5, 'PT', 'WELCOME', 2152),
    (450, 5, 'PT', 'VIP', 922),
    (1990, 10, 'BR', None, 22119),
    (1990, 10, 'BR', 'WELCOME', 21534),
    (1990, 10, 'BR', 'VIP', 20364),
    (1990, 10, 'US', None, 20417),
    (1990, 10, 'US', 'WELCOME', 19877),
    (1990, 10, 'US', 'VIP', 18797),
    (1990, 10, 'PT', None, 23253),
    (1990, 10, 'PT', 'WELCOME', 22638),
    (1990, 10, 'PT', 'VIP', 21408),
    (320, 25, 'BR', None, 8892),
    (320, 25, 'BR', 'WELCOME', 8307),
    (320, 25, 'BR', 'VIP', 7137),
    (320, 25, 'US', None, 8208),
    (320, 25, 'US', 'WELCOME', 7668),
    (320, 25, 'US', 'VIP', 6588),
    (320, 25, 'PT', None, 9348),
    (320, 25, 'PT', 'WELCOME', 8733),
    (320, 25, 'PT', 'VIP', 7503),
    (1990, 50, 'BR', None, 104774),
    (1990, 50, 'BR', 'WELCOME', 104188),
    (1990, 50, 'BR', 'VIP', 103018),
    (1990, 50, 'US', None, 96714),
    (1990, 50, 'US', 'WELCOME', 96174),
    (1990, 50, 'US', 'VIP', 95094),
    (1990, 50, 'PT', None, 110146),
    (1990, 50, 'PT', 'WELCOME', 109532),
    (1990, 50, 'PT', 'VIP', 108302),
    (875, 75, 'BR', None, 69103),
    (875, 75, 'BR', 'WELCOME', 68518),
    (875, 75, 'BR', 'VIP', 67348),
    (875, 75, 'US', None, 63787),
    (875, 75, 'US', 'WELCOME', 63247),
    (875, 75, 'US', 'VIP', 62167),
    (875, 75, 'PT', None, 72646),
    (875, 75, 'PT', 'WELCOME', 72031),
    (875, 75, 'PT', 'VIP', 70801),
    (1990, 100, 'BR', None, 197906),
    (1990, 100, 'BR', 'WELCOME', 197320),
    (1990, 100, 'BR', 'VIP', 196150),
    (1990, 100, 'US', None, 182682),
    (1990, 100, 'US', 'WELCOME', 182142),
    (1990, 100, 'US', 'VIP', 181062),
    (1990, 100, 'PT', None, 208054),
    (1990, 100, 'PT', 'WELCOME', 207440),
    (1990, 100, 'PT', 'VIP', 206210),
    (129, 250, 'BR', None, 32072),
    (129, 250, 'BR', 'WELCOME', 31487),
    (129, 250, 'BR', 'VIP', 30317),
    (129, 250, 'US', None, 29605),
    (129, 250, 'US', 'WELCOME', 29065),
    (129, 250, 'US', 'VIP', 27985),
    (129, 250, 'PT', None, 33717),
    (129, 250, 'PT', 'WELCOME', 33102),
    (129, 250, 'PT', 'VIP', 31872),
]


@pytest.mark.parametrize('unit, qty, country, coupon, expected', CASES)
def test_total(unit, qty, country, coupon, expected):
    order = {'unit': unit, 'qty': qty, 'country': country, 'coupon': coupon}
    got = pricing.total(order['unit'], order['qty'], order['country'], order['coupon'])
    assert isinstance(got, int), f'a total is whole cents, got {got!r}'
    assert got >= 0, 'a coupon never makes an order negative'
    assert got == expected, f'{qty} x {unit} to {country} with coupon {coupon}: expected {expected}, got {got}'


@pytest.mark.parametrize('qty, discount', [(1, 0.0), (9, 0.0), (10, 0.05), (49, 0.05), (50, 0.10), (99, 0.10), (100, 0.15), (5000, 0.15)])
def test_tier(qty, discount):
    assert pricing.tier(qty) == discount
