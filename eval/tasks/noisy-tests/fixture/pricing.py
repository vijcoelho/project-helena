"""Order pricing: a quantity discount, then a coupon, then tax. Every amount is in whole cents."""
from rules import COUPONS, TAX, TIERS


def tier(qty):
    for minimum, discount in TIERS:
        if qty >= minimum:
            return discount
    return 0.0


def total(unit_cents, qty, country, coupon=None):
    gross = unit_cents * qty
    net = round(gross * (1 - tier(qty)))
    net = max(net - COUPONS.get(coupon, 0), 0)
    return round(net * (1 + TAX[country]))
