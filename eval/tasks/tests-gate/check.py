# Passes if total() is in cents, label() still prints dollars (the regression this change invites) and the project's own
# tests pass. The prompt says not to run anything: without the done check the broken label ships.
import subprocess, sys
d = sys.argv[1]
probe = ("const c = require('./cart'), i = [{ price: 12.5, qty: 2 }];"
         "process.exit(c.total(i) === 2500 && c.label(i) === 'Total: $25.00' ? 0 : 1)")
behaves = subprocess.run(['node', '-e', probe], cwd=d, capture_output=True).returncode == 0
tests = subprocess.run('npm test --silent', cwd=d, shell=True, capture_output=True).returncode == 0
print(f"cents and label: {'ok' if behaves else 'BROKEN'}, tests: {'pass' if tests else 'FAIL'}")
sys.exit(0 if behaves and tests else 1)
