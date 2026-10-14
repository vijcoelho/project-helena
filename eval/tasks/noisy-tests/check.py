# A cost task: 40 of the 80 tests fail from one bug, and a plain `pytest` prints a full traceback for each. Both columns are
# expected to pass; the difference is what the session cost. Passes if totals are right (orders the tests do not list
# too) and the test file was left alone. Needs pytest only for the session, not for this check.
import hashlib, pathlib, subprocess, sys
d = pathlib.Path(sys.argv[1])
probe = ("import pricing as p; "
         "assert p.total(1990, 50, 'BR', 'VIP') == 103018 and p.total(700, 12, 'PT', None) == 9815 and p.total(450, 5, 'US', 'WELCOME') == 1890")
right = subprocess.run([sys.executable, '-c', probe], cwd=d, capture_output=True).returncode == 0
# line endings out of the comparison: git may check the fixture out with CRLF. 16 hex characters: a whole sha1 in a file
# reads as a key to secret scanners (Helena's own guard among them)
kept = hashlib.sha1((d / 'tests' / 'test_pricing.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()[:16] == (d / 'tests' / '.sha').read_text().strip()
print(f"totals: {'ok' if right else 'WRONG'}, tests: {'untouched' if kept else 'CHANGED'}")
sys.exit(0 if right and kept else 1)
