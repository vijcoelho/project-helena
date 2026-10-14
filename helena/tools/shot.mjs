// A page at phone and desktop width: does anything stick out sideways, and a picture of each to look at.
//   node shot.mjs <file.html | url> <out-folder>
import { chromium } from 'playwright-core';
import { pathToFileURL } from 'node:url';
import { existsSync } from 'node:fs';
import { resolve, join, basename } from 'node:path';

const [target, out = '.'] = process.argv.slice(2);
if (!target) { console.error('usage: node shot.mjs <file.html | url> [out-folder]'); process.exit(2); }
const url = existsSync(target) ? pathToFileURL(resolve(target)).href : target;
let browser;
for (const opts of [{ channel: 'msedge' }, { channel: 'chrome' }, {}]) {
  try { browser = await chromium.launch(opts); break; } catch {}
}
if (!browser) { console.error('no browser: install Edge/Chrome'); process.exit(2); }
let wide = 0;
for (const width of [375, 1440]) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const file = join(out, `${basename(target).replace(/\W+/g, '-')}-${width}.png`);
  await page.screenshot({ path: file });
  console.log(`${width}px: ${over > 0 ? `OVERFLOW ${over}px` : 'no overflow'}  ${file}`);
  wide += over > 0;
  await page.close();
}
await browser.close();
process.exit(wide ? 1 : 0);
