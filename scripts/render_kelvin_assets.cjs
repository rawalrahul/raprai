/**
 * Render Kelvin's Telegram stickers and bot avatar from frontend2/js/kelvin.js,
 * so the images always match the in-app character.
 *
 *   npm i -g playwright   (Chromium is enough)
 *   node scripts/render_kelvin_assets.cjs
 *
 * Writes PNGs (stickers, tray faces, avatar) to frontend2/assets/kelvin/.
 * Convert the stickers to WEBP with:
 *   python scripts/png_to_webp.py
 */
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'frontend2', 'assets', 'kelvin');
const STICKERS = ['done', 'error', 'approval', 'working', 'idle'];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const page = await browser.newPage({ viewport: { width: 640, height: 640 } });
  const css = fs.readFileSync(path.join(ROOT, 'frontend2', 'css', 'kelvin.css'), 'utf8');
  const js = fs.readFileSync(path.join(ROOT, 'frontend2', 'js', 'kelvin.js'), 'utf8');
  await page.setContent(`<!doctype html><html data-kelvin="still"><head><style>
    ${css}
    html, body { margin: 0; background: transparent; font-family: Inter, Arial, sans-serif; }
    #s { width: 512px; height: 512px; display: block; }
    #a { width: 640px; height: 640px; display: grid; place-items: center;
         background: radial-gradient(circle at 50% 58%, #3a2a12 0%, #17120b 62%, #0f0d0b 100%); }
    #a > span { width: 470px; height: 500px; }
  </style></head><body><div id="s"></div><div id="a"><span></span></div><script>${js}</script></body></html>`);

  // Stickers: transparent 512x512 with the state effects drawn around Kelvin.
  for (const mood of STICKERS) {
    await page.evaluate((m) => {
      const host = document.getElementById('s');
      host.innerHTML = '';
      Kelvin.mount(host, { pokeable: false, track: false }).setState(m);
    }, mood);
    await page.waitForTimeout(250);
    await page.locator('#s').screenshot({ path: path.join(OUT, `sticker-${mood}.png`), omitBackground: true });
  }

  // Tray badge faces: head only, transparent, one per mood (helm/kelvin_status.py adds the colour).
  await page.evaluate(() => {
    const host = document.getElementById('s');
    host.style.width = host.style.height = '128px';
  });
  for (const mood of ['idle', 'working', 'approval', 'done', 'error']) {
    await page.evaluate((m) => {
      const host = document.getElementById('s');
      host.innerHTML = '';
      Kelvin.mount(host, { overlays: false, pokeable: false, track: false, viewBox: '-66 -166 132 132' }).setState(m);
    }, mood);
    await page.waitForTimeout(150);
    await page.locator('#s').screenshot({ path: path.join(OUT, `tray-${mood}.png`), omitBackground: true });
  }

  // Avatar: square, opaque, Kelvin centred (Telegram crops it to a circle).
  await page.evaluate(() => {
    document.getElementById('s').remove();
    Kelvin.mount(document.querySelector('#a > span'), { overlays: false, pokeable: false, track: false });
  });
  await page.waitForTimeout(250);
  await page.locator('#a').screenshot({ path: path.join(OUT, 'avatar.png') });

  await browser.close();
  console.log('Wrote', STICKERS.length, 'stickers and avatar.png to', OUT);
})();
