// Checks the contrast of every visible text on a page (WCAG AA), on desktop and on a phone.
//   node contrast.mjs <file.html | http://localhost:PORT>
// Exits 1 and lists each unreadable text (selector, color, background, ratio, minimum). Exits 0 if everything passes.
import { chromium } from 'playwright-core';
import { pathToFileURL } from 'node:url';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

const target = process.argv[2];
if (!target) { console.error('usage: node contrast.mjs <file.html | url>'); process.exit(2); }
const url = existsSync(target) ? pathToFileURL(resolve(target)).href : target;

let browser;
for (const opts of [{ channel: 'msedge' }, { channel: 'chrome' }, {}]) {
  try { browser = await chromium.launch(opts); break; } catch {}
}
if (!browser) { console.error('no browser: install Edge/Chrome or run `npx playwright install chromium`'); process.exit(2); }

const failures = new Map();
for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  const page = await browser.newPage({ viewport });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800); // let entrance animations finish
  const found = await page.evaluate(() => {
    const rgba = s => { const m = s.match(/[\d.]+/g) || [0, 0, 0, 0]; return [+m[0], +m[1], +m[2], m[3] === undefined ? 1 : +m[3]]; };
    const lum = ([r, g, b]) => { const c = [r, g, b].map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
    const over = (fg, bg) => [0, 1, 2].map(i => fg[i] * fg[3] + bg[i] * (1 - fg[3]));
    const background = el => {
      // ponytail: skips image/gradient backgrounds (left for a manual look); only blends solid colors
      const layers = [];
      for (let e = el; e; e = e.parentElement) {
        const cs = getComputedStyle(e);
        if (cs.backgroundImage !== 'none') return null;
        const c = rgba(cs.backgroundColor);
        if (c[3] > 0) { layers.push(c); if (c[3] === 1) break; }
      }
      return layers.reverse().reduce((acc, c) => over(c, acc), [255, 255, 255]);
    };
    const name = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.classList.length ? '.' + [...el.classList].join('.') : '');
    const out = [];
    for (const el of document.querySelectorAll('body *')) {
      const text = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
      if (!text) continue;
      const cs = getComputedStyle(el), r = el.getBoundingClientRect();
      if (cs.visibility === 'hidden' || +cs.opacity === 0 || r.width === 0 || r.height === 0) continue;
      const bg = background(el);
      if (!bg) continue;
      const color = over(rgba(cs.color), bg);
      const [a, b] = [lum(color), lum(bg)].sort((x, y) => y - x);
      const ratio = (a + 0.05) / (b + 0.05);
      const px = parseFloat(cs.fontSize), bold = +cs.fontWeight >= 700;
      const minimum = px >= 24 || (px >= 18.66 && bold) ? 3 : 4.5;
      if (ratio < minimum) out.push({ sel: name(el), text: text.slice(0, 40), color: cs.color, bg: `rgb(${bg.map(Math.round)})`, ratio: +ratio.toFixed(2), minimum });
    }
    return out;
  });
  for (const f of found) failures.set(f.sel + f.text, { ...f, width: viewport.width });
  await page.close();
}
await browser.close();

if (!failures.size) { console.log('contrast OK: every visible text passes WCAG AA'); process.exit(0); }
console.log(`${failures.size} unreadable text(s):`);
for (const f of failures.values()) console.log(`- ${f.sel} "${f.text}" color ${f.color} on ${f.bg}: ${f.ratio}:1 (minimum ${f.minimum}:1, ${f.width}px screen)`);
process.exit(1);
