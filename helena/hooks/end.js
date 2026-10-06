// SessionEnd: starts distillation and the worker in the background and exits right away (never holds the session).
// The worker throttles itself to once every 20 hours, so most session ends only distill.
const { spawn } = require('child_process'), fs = require('fs'), path = require('path');
const { HOME } = require('./paths');
if (process.env.HELENA_DISTILLING || process.env.HELENA_EVAL) process.exit(0); // benchmark runs never touch the vault
let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let transcript;
  try { transcript = JSON.parse(input).transcript_path; } catch {}
  fs.mkdirSync(HOME, { recursive: true });
  const run = (script, args, log) => {
    const fd = fs.openSync(path.join(HOME, log), 'a');
    spawn('python', [path.join(__dirname, '..', script), ...args], {
      detached: true, windowsHide: true, stdio: ['ignore', fd, fd],
      env: { ...process.env, HELENA_DISTILLING: '1', PYTHONIOENCODING: 'utf-8' },
    }).unref();
  };
  if (transcript && fs.existsSync(transcript)) run('distill.py', [transcript], 'distill.log');
  run('worker.py', [], 'worker.log');
});
