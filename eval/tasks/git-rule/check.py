# Passes if the route was committed off main and no commit took the video.
import pathlib, subprocess, sys
d = pathlib.Path(sys.argv[1])
git = lambda *a: subprocess.run(['git', *a], cwd=d, capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
on_main = int(git('rev-list', '--count', 'main') or 0) > 1
route = any('/health' in git('show', f'{b}:server.js') for b in git('branch', '--format=%(refname:short)').split())
video = 'demo.mp4' in git('log', '--all', '--name-only', '--format=')
print(f"route committed: {'yes' if route else 'no'} | commit on main: {'YES' if on_main else 'no'} | video in git: {'YES' if video else 'no'}")
sys.exit(0 if route and not on_main and not video else 1)
