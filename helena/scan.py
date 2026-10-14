"""Security scan of a skill before it joins the library: an agent executes what a skill says, so a malicious one is a backdoor.
No LLM: patterns for the attacks found in public skill hubs (pipe-to-shell installers, credential reads, exfiltration
webhooks, instructions to hide things from the user, invisible text).

    python helena/scan.py <skill folder> [...]     # exit 2 = critical finding, 1 = warnings only, 0 = clean

library.py runs it on install and skips a skill with a critical finding unless you pass --trust.
A clean scan is not a proof of safety; read a skill you do not know before trusting it.
"""
import pathlib, re, sys

CREDS = r'(~/\.ssh|\bid_(rsa|ed25519)\b|\.aws/credentials|\.git-credentials|\.config/gh/hosts|\.npmrc|\.pypirc|Login Data|keychain)'
# calibrated on a real library of 107 skills: what legit skills do (install with curl | sh, mention ~/.ssh, document a
# --dangerously-skip-permissions run) only warns; critical is for what only an attack needs
CRITICAL = [
    (r'base64\s+(-d|--decode)[^\n]*\|\s*(ba)?sh|eval\s*\(\s*atob\(|exec\s*\(\s*base64\.b64decode|FromBase64String', 'runs hidden (encoded) code'),
    (r'\b(cat|type|Get-Content|cp|copy|scp|tar|zip|curl|open\()[^\n]*' + CREDS, 'reads or copies credentials'),
    (r'discord(app)?\.com/api/webhooks|hooks\.slack\.com/services|webhook\.site|requestbin|pastebin\.com/api|ngrok\.io|'
     r'\bcurl\b[^\n]*(-d|--data|-F)\s*["\']?@', 'sends data to an outside endpoint'),
    (r'ignore\s+(all\s+)?(previous|prior|above)\s+instructions|do\s+not\s+(tell|inform|mention\s+(it\s+)?to)\s+the\s+user(?!\s+to\b)|'
     r'without\s+(telling|informing)\s+the\s+user|(disable|bypass|turn\s+off)\s+(the\s+)?(hooks?|guard)\b', 'tells the AI to hide things or drop its guardrails'),
    ('[\u200e\u200f\u202a-\u202e\u2066-\u2069]', 'direction-flipping characters (text that reads differently than it runs)'),
    # instructions fetched at run time: what the URL says tomorrow is what the AI does (docs that say "follow the
    # instructions on the page" are common and are not this: it takes "follow what it says" about a download, or code that evals one)
    (r'\b(curl|wget|iwr|Invoke-WebRequest|fetch|download)\b[^\n]*https?://[^\n]*\b(follow|obey|do|carry\s+out)\s+(what|whatever)\s+(it|they|that|the\s+(file|page|response))\s+says|'
     r'\b(eval|exec)\s*\(\s*(await\s+)?(requests\.get|urllib\.request\.urlopen|urlopen|fetch)\b', 'runs instructions or code fetched at run time'),
]
WARN = [
    ('\u200b|(?<!^)\ufeff', 'invisible characters'),
    (r'(curl|wget|iwr|Invoke-WebRequest)\b[^\n|]*\|\s*(sudo\s+)?((ba|z)?sh|iex|Invoke-Expression)\b', 'installs by piping a download into a shell'),
    (CREDS, 'mentions a credentials file'),
    (r'dangerously-skip-permissions|bypassPermissions', 'runs an AI with permissions off'),
    (r'\brm\s+-\w*r\w*f|\bchmod\s+777\b|\bsudo\b', 'destructive or privileged shell command'),
    (r'\bos\.system\(|shell\s*=\s*True|\beval\s*\(|\bexec\s*\(|child_process', 'runs commands or code it builds'),
    (r'(^|[\s"\'/])\.env\b', 'touches a .env file'),
    # a payload behind a condition (env var, CI flag, date, host, user) that fetches, decodes or evals: cloaked from a test run
    (r'\b(if|when|unless)\b[^\n]*(os\.environ|getenv|process\.env|\$env:|hostname|getuser|whoami|\bdatetime\b|Date\.now|new Date)[^\n]*(\n[^\n]*){0,2}?'
     r'(curl|wget|\beval\b|\bexec\b|base64|\|\s*(ba)?sh|os\.system|child_process|Invoke-Expression|\biex\b)', 'runs something only when an env var, date, host or user matches'),
    (r'\beval\s+"?\$\(\s*(curl|wget)|\b(iex|Invoke-Expression)\b[^\n]*\b(iwr|Invoke-WebRequest|DownloadString)\b', 'evals a download'),
]
BLOB = r'[A-Za-z0-9+/]{300,}={0,2}|\b(?:[0-9a-f]{2}){150,}\b'  # base64 or hex of a few hundred characters
DECODE = r'b64decode|atob\(|base64\s+(-d|--decode)|FromBase64|unhexlify|fromhex|Buffer\.from|xxd\s+-r'
RUN_OR_WRITE = r'\beval\b|\bexec\b|os\.system|subprocess|child_process|\|\s*(ba)?sh\b|\biex\b|Invoke-Expression|write_bytes|writeFile|Out-File|Set-Content|open\([^)]*[\'"]wb?[\'"]'
TEXT = {'.md', '.txt', '.py', '.js', '.mjs', '.cjs', '.ts', '.sh', '.ps1', '.bat', '.cmd', '.json', '.yaml', '.yml', '.toml', ''}


def scan(folder):
    """[(level, 'file:line', why)] for a skill folder (or a single file)."""
    folder = pathlib.Path(folder)
    files = [folder] if folder.is_file() else [f for f in folder.rglob('*') if f.is_file() and f.suffix.lower() in TEXT
                                                and not {'node_modules', '.git'} & set(f.parts) and f.stat().st_size < 1 << 20]
    found = []
    for f in files:
        text = f.read_text(encoding='utf-8', errors='ignore')
        for level, rules in (('critical', CRITICAL), ('warn', WARN)):
            for pattern, why in rules:
                for m in re.finditer(pattern, text, re.I | re.M):
                    found.append((level, f'{f.relative_to(folder) if f != folder else f.name}:{text.count(chr(10), 0, m.start()) + 1}', why))
                    break  # one hit per rule per file is enough to read it
        b = re.search(BLOB, text)
        if b and re.search(DECODE, text, re.I) and re.search(RUN_OR_WRITE, text):
            found.append(('critical', f'{f.relative_to(folder) if f != folder else f.name}:{text.count(chr(10), 0, b.start()) + 1}',
                          'a long encoded blob that is decoded and run or written to disk'))
    return found


def verdict(found):
    return 'critical' if any(l == 'critical' for l, _, _ in found) else 'warn' if found else 'clean'


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    worst = 0
    for target in sys.argv[1:] or sys.exit(__doc__):
        found = scan(target)
        print(f'{target}: {verdict(found)}')
        for level, where, why in found:
            print(f'  {level:8} {where}  {why}')
        worst = max(worst, {'clean': 0, 'warn': 1, 'critical': 2}[verdict(found)])
    sys.exit(worst)
