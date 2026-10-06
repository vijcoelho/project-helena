// Where Helena keeps the user's data. Everything learned lives here, outside the plugin, so updates never wipe it.
//   ~/.helena/vault      one line: path of the Obsidian vault (default ~/Helena)
//   ~/.helena/kits.json  the user's kits (see helena/kits.example.json)
//   ~/.helena/library/   skills that only load when a kit asks for them
const fs = require('fs'), path = require('path'), os = require('os');
const HOME = path.join(os.homedir(), '.helena');
const readVault = () => { try { return fs.readFileSync(path.join(HOME, 'vault'), 'utf8').trim(); } catch {} };
const VAULT = process.env.HELENA_VAULT || readVault() || path.join(os.homedir(), 'Helena');
module.exports = { HOME, VAULT, MEMORY: path.join(VAULT, 'Memory'), LIBRARY: path.join(HOME, 'library'), KITS: path.join(HOME, 'kits.json') };
