# Passes if multiply exists AND the handoff is in the agreed place and format.
import sys, pathlib, subprocess
d = pathlib.Path(sys.argv[1])
ok = subprocess.run(['node', '-e', "if(require('./calc.js').multiply(3,4)!==12)process.exit(1)"], cwd=d).returncode == 0
h = d / 'HANDOFF.md'
text = h.read_text(errors='ignore').lower() if h.exists() else ''
ok = ok and all(s in text for s in ('## done', '## next', '## how to run'))
print(f"multiply + HANDOFF.md: {'ok' if ok else 'no'}")
sys.exit(0 if ok else 1)
