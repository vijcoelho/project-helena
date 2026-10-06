"""Tests distillation: a session with durable corrections must become memory; a trivial session, nothing.

    python eval/test_distill.py
"""
import json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def session(folder, name, turns):
    f = folder / f'{name}.jsonl'
    with open(f, 'w', encoding='utf-8') as out:
        for who, text in turns:
            if who == 'u':
                out.write(json.dumps({'type': 'user', 'message': {'content': text}}, ensure_ascii=False) + '\n')
            else:
                out.write(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}},
                                     ensure_ascii=False) + '\n')
    return f


def distill(transcript, vault):
    subprocess.run([sys.executable, str(ROOT / 'helena' / 'distill.py'), str(transcript), str(vault)],
                   check=True, timeout=400)
    return ' '.join(p.read_text(encoding='utf-8').lower() for p in vault.rglob('*.md'))


with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    rich = session(tmp, 'rich', [
        ('u', 'generate the hero images for the bakery landing page'),
        ('ai', 'I need a GEMINI_API_KEY to generate the images. Can you send it?'),
        ('u', 'there is no gemini key, I have the google pro plan, use the agy command in bash to make images, it is always like that'),
        ('ai', 'Done, I generated the 3 images with agy in assets/img.'),
        ('u', 'run the project so I can see it'),
        ('ai', 'Started on http://localhost:3000.'),
        ('u', 'no!! 3000 is my other project, never kill it, always run on another port like 3001'),
        ('ai', 'Sorry. Running on http://localhost:3001 and 3000 is untouched.'),
        ('u', 'my stripe key is ' + 'sk_' + 'live_51abcdefghijklmnopqrstuvwxyz0123, save it in .env'),
        ('ai', 'Saved in .env.'),
    ])
    text = distill(rich, tmp / 'vault')
    ok_agy = 'agy' in text
    ok_port = '3000' in text or 'port' in text
    ok_secret = 'sk_live_51abc' not in text

    trivial = session(tmp, 'trivial', [
        ('u', 'what is 2+2?'), ('ai', '4.'), ('u', 'thanks'), ('ai', 'You are welcome!')])
    ok_trivial = distill(trivial, tmp / 'vault2') == ''

    for name, ok in [('remembered agy', ok_agy), ('remembered port 3000', ok_port),
                     ('did not leak the secret', ok_secret), ('trivial session wrote nothing', ok_trivial)]:
        print(f"{'PASS' if ok else 'fail'}  {name}")
    sys.exit(0 if all([ok_agy, ok_port, ok_secret, ok_trivial]) else 1)
