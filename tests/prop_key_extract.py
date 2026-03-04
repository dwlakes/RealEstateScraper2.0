import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
import regex as re

TEST_URL = "https://www.properstar.com/listing/104687773"

async def fetch_html(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = await ctx.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_selector(".location-map", timeout=5000)
        html = await page.content()
        await browser.close()
    return html

def get_coords(container):
    static_map = container.find(class_="static-map-image")
    style = static_map.get("style","") if static_map else ""
    # Find coordinates from Google API call
    print(f"Style: {style}")
    coords_regex = re.search(r'center=([-\d.]+)%2C([-\d.]+)', str(container))
    coords_dict = {"lat": coords_regex.group(1), "lon":coords_regex.group(2)}
    return coords_dict


def parse_features(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="location-map")
    print(container)
    if not container:
        print("WARNING — location-map container not found")
    if container:
        coords = get_coords(container)
        # coords_tuple = (coords.group(1), coords.group(2))
    features = {}
    for item in soup.find_all(class_="feature-item"):
        key = item.find(class_="property-key")
        value = item.find(class_="property-value")
        if key and value:
            features[key.get_text(strip=True)] = value.get_text(strip=True)
            features.update(coords)
    return features

html = asyncio.run(fetch_html(TEST_URL))
features = parse_features(html)
print(features)
for key, val in features.items():
    print(key, val)
    