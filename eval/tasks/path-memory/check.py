# Passes if src/billing.js exports lateFee and follows the path-scoped rule (Math.ceil instead of Math.round/Math.floor).
import pathlib, sys

d = pathlib.Path(sys.argv[1])
src = (d / 'src' / 'billing.js').read_text(encoding='utf-8')
has_fn = 'lateFee' in src
uses_ceil = 'Math.ceil' in src and 'Math.round' not in src and 'Math.floor' not in src
print(f"lateFee={'yes' if has_fn else 'no'}, ceil_rule={'yes' if uses_ceil else 'no'}")
sys.exit(0 if has_fn and uses_ceil else 1)
