#!/usr/bin/env python3
"""Generate PWA icons for Morning Brief from icon-master.svg via bundled Chromium.

Renders the master SVG to PNG at the sizes the app needs:
  public/icon-512.png  (512x512, manifest)
  public/icon-192.png  (192x192, manifest + favicon fallback)
  public/icon-180.png  (180x180, apple-touch-icon)

PIL cannot reproduce the SVG's glow/gradients, so we rasterize with the
Chromium that playwright already bundles. Run from the repo root:
    python3 scripts/gen_icons.py
"""
import asyncio
import base64
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "icon-master.svg")
TARGETS = {
    "public/icon-512.png": 512,
    "public/icon-192.png": 192,
    "public/icon-180.png": 180,
}


async def main():
    from playwright.async_api import async_playwright

    with open(MASTER) as f:
        b64 = base64.b64encode(f.read().encode()).decode()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for rel, size in TARGETS.items():
            page = await browser.new_page(
                viewport={"width": size, "height": size}, device_scale_factor=1
            )
            await page.set_content(
                f'<body style="margin:0">'
                f'<img src="data:image/svg+xml;base64,{b64}" '
                f'width="{size}" height="{size}"></body>'
            )
            out = os.path.join(ROOT, rel)
            await page.locator("img").screenshot(path=out)
            await page.close()
            print("wrote", rel, f"({size}x{size})")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
