// SessionEnd: starts distillation and the worker in the background and exits right away (never holds the session).
// The worker throttles itself to once every 20 hours, so most session ends only distill.
const fs = require('fs');
const { bg } = require('./paths');
if (process.env.HELENA_DISTILLING || process.env.HELENA_EVAL) process.exit(0); // benchmark runs never touch the vault
let input = '';
process.stdin.on('data', d => (input += d)).on('end', () => {
  let transcript;
  try { transcript = JSON.parse(input).transcript_path; } catch {}
  if (transcript && fs.existsSync(transcript)) bg('distill.py', [transcript], 'distill.log');
  bg('worker.py', [], 'worker.log');
});
