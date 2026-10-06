# Passes if the handoff's next step was done AND HANDOFF.md no longer lists it as pending.
import sys, subprocess, pathlib, re
d = pathlib.Path(sys.argv[1])
js = """const c=require('./calc.js');
if(c.divide(6,3)!==2)process.exit(1);
try{c.divide(1,0);process.exit(1)}catch(e){if(!/zero/.test(e.message))process.exit(1)}"""
if subprocess.run(['node', '-e', js], cwd=d).returncode:
    print('divide: no')
    sys.exit(1)
text = (d / 'HANDOFF.md').read_text(errors='ignore').lower()
pending = re.search(r'## next(.*?)(\n## |\Z)', text, re.S)
still = bool(pending and 'divide' in pending.group(1))
print(f"divide: ok | still listed as next: {'yes' if still else 'no'}")
sys.exit(1 if still else 0)
