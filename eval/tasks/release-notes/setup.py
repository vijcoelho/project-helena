# A repo tagged v1.2.0 with 120 commits after it, each with a body, the way a team that writes commit messages leaves it.
# Five of them are features; the rest is the usual noise. A plain `git log v1.2.0..HEAD` prints about 1,400 lines.
import pathlib, subprocess, sys
d = pathlib.Path(sys.argv[1])
g = lambda *a: subprocess.run(['git', '-c', 'user.email=eval@helena', '-c', 'user.name=eval', *a], cwd=d, check=True, capture_output=True)
FEATURES = {8: 'feat: export orders as CSV from the orders page', 37: 'feat: two-factor login with an authenticator app',
            64: 'feat: saved filters on the customer list', 91: 'feat: weekly sales summary by email', 113: 'feat: dark mode in the dashboard'}
NOISE = ['chore: bump dependencies', 'refactor: split the {m} module', 'fix: flaky test in {m}', 'chore: lint {m}', 'test: cover {m} edge cases',
         'refactor: rename helpers in {m}', 'ci: cache the install step', 'fix: typo in a log line of {m}', 'docs: comment the {m} entry point']
MODULES = ['orders', 'billing', 'customers', 'auth', 'reports', 'dashboard', 'mailer']
BODY = ('Context: part of the cleanup agreed in the planning meeting.\nWhat changed: see the diff, nothing outside this module.\n'
        'Risk: low, covered by the existing tests.\nRollback: revert this commit.\nReviewed-by: the team on call that week.')

g('init', '-q'); g('add', '.'); g('commit', '-qm', 'release: 1.2.0'); g('tag', 'v1.2.0')
for i in range(1, 121):
    module = MODULES[i % len(MODULES)]
    (d / 'src' / f'{module}.js').open('a').write(f'// change {i}\n')
    g('commit', '-qam', FEATURES.get(i) or NOISE[i % len(NOISE)].format(m=module), '-m', BODY)
