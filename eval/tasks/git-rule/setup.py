# Repo on main with the .helena/git agreed in an earlier session ("never commit to main", "no videos") and a loose video.
import pathlib, subprocess, sys
d = pathlib.Path(sys.argv[1])
(d / 'demo.mp4').write_bytes(b'\0' * 2048)
g = lambda *a: subprocess.run(['git', '-c', 'user.email=eval@helena', '-c', 'user.name=eval', *a], cwd=d, check=True, capture_output=True)
g('init', '-q', '-b', 'main'); g('add', 'server.js', 'package.json', '.helena'); g('commit', '-qm', 'initial')
