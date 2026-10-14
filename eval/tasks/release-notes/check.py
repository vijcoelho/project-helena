# A cost task: the answer is in 120 commits, and a plain `git log` of them is about 1,400 lines. Both columns are expected
# to pass; the difference is what the session cost. Passes if RELEASE.md names the five features (three of them are older
# than the 20 commits Helena's trim shows first, so a session that stops at those fails).
import pathlib, re, sys
f = pathlib.Path(sys.argv[1]) / 'RELEASE.md'
text = f.read_text(encoding='utf-8', errors='replace').lower() if f.exists() else ''
want = {'CSV export': r'csv', 'two-factor': r'two.factor|2fa|authenticator', 'saved filters': r'saved filters?',
        'weekly summary': r'weekly', 'dark mode': r'dark mode'}
missing = [name for name, pattern in want.items() if not re.search(pattern, text)]
print('all five features' if not missing else ('no RELEASE.md' if not text else 'missing: ' + ', '.join(missing)))
sys.exit(1 if missing else 0)
