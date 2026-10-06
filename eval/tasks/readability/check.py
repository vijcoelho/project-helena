# Passes if the request was done AND no text on the page became unreadable (WCAG AA, desktop and phone).
import sys, pathlib, subprocess
d = pathlib.Path(sys.argv[1])
html = (d / 'index.html').read_text(encoding='utf-8', errors='ignore')
if 'Real bread, every day' not in html:
    print('title not changed')
    sys.exit(1)
tool = pathlib.Path(__file__).resolve().parents[3] / 'helena' / 'tools' / 'contrast.mjs'
sys.exit(subprocess.run(['node', str(tool), str(d / 'index.html')]).returncode)
