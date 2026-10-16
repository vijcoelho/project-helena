// The native window on Windows: shell/Helena.cs, compiled once into ~/.helena/app-shell with the csc that ships with
// Windows. The WebView2 DLLs it needs come from the official NuGet package, downloaded once. Anything missing or
// failing returns '' and the app opens in an Edge app window instead, as before.
const fs = require('fs'), path = require('path'), https = require('https'), { execFileSync } = require('child_process');
const { HOME } = require('../hooks/paths');
const DIR = path.join(HOME, 'app-shell'), EXE = path.join(DIR, 'Helena.exe'), SRC = path.join(__dirname, 'shell', 'Helena.cs');
const WV2 = '1.0.4191.47';  // the Microsoft.Web.WebView2 package version it is built against
const CSC = path.join(process.env.WINDIR || 'C:\\Windows', 'Microsoft.NET', 'Framework64', 'v4.0.30319', 'csc.exe');
const DLLS = ['Microsoft.Web.WebView2.Core.dll', 'Microsoft.Web.WebView2.WinForms.dll', 'WebView2Loader.dll'];

function get(url, file, hops = 5) {
  return new Promise((ok, bad) => https.get(url, r => {
    if (r.statusCode >= 300 && r.statusCode < 400 && r.headers.location && hops) { r.resume(); return get(new URL(r.headers.location, url).href, file, hops - 1).then(ok, bad); }
    if (r.statusCode !== 200) { r.resume(); return bad(new Error(`HTTP ${r.statusCode}`)); }
    r.pipe(fs.createWriteStream(file)).on('finish', ok).on('error', bad);
  }).on('error', bad));
}

// an .ico is a 22-byte header around a PNG (Windows reads PNG icons since Vista)
function ico(png) {
  const h = Buffer.alloc(22);
  h.writeUInt16LE(1, 2); h.writeUInt16LE(1, 4);  // type icon, one image
  h.writeUInt16LE(32, 12);                          // 256x256 (0 = 256), 32 bits per pixel
  h.writeUInt32LE(png.length, 14); h.writeUInt32LE(22, 18);
  return Buffer.concat([h, png]);
}

async function ensure() {
  if (process.platform !== 'win32' || !fs.existsSync(CSC)) return '';
  try {
    if (!(fs.existsSync(EXE) && fs.statSync(EXE).mtimeMs > fs.statSync(SRC).mtimeMs)) await build();
  } catch { return ''; }
  // Helena.exe with no address (the Start menu) starts this plugin version's server itself: node, then server.js
  try { fs.writeFileSync(path.join(DIR, 'launch.txt'), `${process.execPath}\n${path.join(__dirname, 'server.js')}\n`); } catch {}
  const lnk = path.join(process.env.APPDATA || '', 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Helena.lnk'), q = s => s.replace(/'/g, "''");
  if (process.env.APPDATA && !fs.existsSync(lnk)) try {
    execFileSync('powershell', ['-NoProfile', '-Command', `$s = (New-Object -ComObject WScript.Shell).CreateShortcut('${q(lnk)}'); ` +
      `$s.TargetPath = '${q(EXE)}'; $s.IconLocation = '${q(path.join(DIR, 'helena.ico'))}'; $s.Save()`], { windowsHide: true, stdio: 'ignore' });
  } catch {}
  return EXE;
}

async function build() {
  fs.mkdirSync(DIR, { recursive: true });
  if (!DLLS.every(d => fs.existsSync(path.join(DIR, d)))) {
    const zip = path.join(DIR, 'webview2.zip'), pkg = path.join(DIR, 'pkg');
    await get(`https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2/${WV2}`, zip);
    execFileSync('powershell', ['-NoProfile', '-Command', `Expand-Archive -Force -LiteralPath '${zip}' -DestinationPath '${pkg}'`], { windowsHide: true });
    for (const [d, from] of [[DLLS[0], 'lib/net462'], [DLLS[1], 'lib/net462'], [DLLS[2], 'runtimes/win-x64/native']])
      fs.copyFileSync(path.join(pkg, from, d), path.join(DIR, d));
    fs.rmSync(pkg, { recursive: true, force: true }); fs.rmSync(zip, { force: true });
  }
  fs.writeFileSync(path.join(DIR, 'helena.ico'), ico(fs.readFileSync(path.join(__dirname, 'icon.png'))));
  execFileSync(CSC, ['/target:winexe', '/platform:x64', '/nologo', '/optimize+', `/out:${EXE}`, `/win32icon:${path.join(DIR, 'helena.ico')}`,
    '/reference:System.dll', '/reference:System.Drawing.dll', '/reference:System.Windows.Forms.dll',
    `/reference:${path.join(DIR, DLLS[0])}`, `/reference:${path.join(DIR, DLLS[1])}`, SRC], { windowsHide: true, stdio: 'pipe' });
}

module.exports = { ensure, EXE };
if (require.main === module) ensure().then(p => console.log(p || 'no native window: the app uses an Edge window'));
