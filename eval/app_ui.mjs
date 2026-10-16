// node eval/app_ui.mjs <url> <outdir> (app running: node helena/app/server.js --serve --no-open --port N): every size change x every button, checking after each step that the window is still usable
import { createRequire } from 'node:module';
const require = createRequire(new URL('../helena/tools/package.json', import.meta.url));
const { chromium } = require('playwright-core');
const [url, out] = process.argv.slice(2);
const browser = await chromium.launch({ channel: 'msedge' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [], bad = [];
page.on('pageerror', e => errors.push(e.message));
// usable = bar at the top, full width; the active pane's box on screen; nothing scrolled the page
const check = async step => {
  const r = await page.evaluate(() => {
    const box = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
    const bar = box('.bar'), t = box('.pane.active textarea'), send = box('.pane.active .send');
    return { bar, t, send, w: innerWidth, h: innerHeight, sx: scrollX, sy: scrollY, docW: document.documentElement.scrollWidth, cls: document.body.className };
  });
  const ok = r.bar && r.bar.y === 0 && r.bar.x === 0 && Math.abs(r.bar.w - r.w) < 1 && r.t && r.t.w > 100 && r.send.y > 0 && r.send.y + r.send.h <= r.h && !r.sx && !r.sy && r.docW <= r.w;
  if (!ok) { bad.push(step); await page.screenshot({ path: `${out}/r-bad-${bad.length}.jpg`, type: 'jpeg', quality: 70 }); }
  console.log(ok ? 'ok ' : 'BAD', step, ok ? '' : JSON.stringify(r));
};
const size = async (w, h) => { await page.setViewportSize({ width: w, height: h }); await page.waitForTimeout(250); };
const click = async s => { await page.click(s); await page.waitForTimeout(250); };
await page.goto(url);
await page.waitForTimeout(2000);
const SIZES = [[1440, 900], [1100, 800], [700, 800], [375, 812], [1920, 1032]];
await check('start');
// sessions button and the drawer at every size, then every other size after it
for (const [w, h] of SIZES) {
  await size(w, h); await check(`size ${w}`);
  await click('#sideBtn'); await check(`side ${w}`);
  for (const [w2, h2] of SIZES) { await size(w2, h2); await check(`side ${w} -> ${w2}`); }
  await size(w, h); await click('#sideBtn').catch(() => {}); await page.keyboard.press('Escape');
  await click('#panelBtn'); await check(`drawer ${w}`);
  for (const [w2, h2] of SIZES) { await size(w2, h2); await check(`drawer ${w} -> ${w2}`); }
  await page.keyboard.press('Escape'); await size(w, h); await check(`esc ${w}`);
}
// panes: split to four at each size, close back to one
for (const [w, h] of SIZES) {
  await size(w, h);
  for (let i = 0; i < 3; i++) await click('#split');
  await check(`4 panes ${w}`);
  await page.keyboard.press('Control+2'); await check(`ctrl+2 ${w}`);
  for (const [w2, h2] of SIZES) { await size(w2, h2); await check(`4 panes ${w} -> ${w2}`); }
  await size(1440, 900);
  while (await page.locator('.pane').count() > 1) await page.locator('.pane.active .pclose').click();
  await check(`back to 1 ${w}`);
}
// slash and model menus at a phone size
await size(375, 812);
await page.locator('.pane.active textarea').fill('/');
await page.locator('.pane.active textarea').dispatchEvent('input');
await check('slash menu phone');
await page.keyboard.press('Escape');
await page.locator('.pane.active .model').click();
await check('model menu phone');
await page.screenshot({ path: `${out}/r-model-phone.jpg`, type: 'jpeg', quality: 70 });
console.log('bad steps:', bad.length, 'errors:', JSON.stringify(errors));
await browser.close();
