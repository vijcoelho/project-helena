"""The price list. Sales edits this file; pricing.py only reads it."""
TIERS = sorted([(100, 0.15), (10, 0.05), (50, 0.10)])  # (minimum quantity, discount)
COUPONS = {'WELCOME': 500, 'VIP': 1500}                # cents off the order
TAX = {'BR': 0.17, 'US': 0.08, 'PT': 0.23}
