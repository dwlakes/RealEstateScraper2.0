import asyncio
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from schema import Property, PropertyList

# --- Paths ---
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "properstar_listings.csv"

BASE_URL = "https://www.properstar.com"
TARGET_URL = f"{BASE_URL}/colombia/buy"

async def fetch_html(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="es-CO",
        )
        page = await ctx.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        html = await page.content()
        await browser.close()
    return html

def parse_listings(html: str) -> list[Property]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="items-list-small")
    if not container:
        print("WARNING — listing container not found")
        return []

    cards = container.find_all(class_=lambda c: c and ("card-full" in c or "card-extended" in c))
    listings = []
    for card in cards:
        # URL
        link = card.find("a", href=True)
        href = link["href"] if link else ""
        url = (BASE_URL + href) if href.startswith("/") else href

        # Price
        price_el = card.find(class_="listing-price-main")
        price = price_el.get_text(strip=True) if price_el else ""

        # Location
        loc_el = card.find(class_="item-highlights")
        location = loc_el.get_text(separator=" ", strip=True) if loc_el else ""

        if price or location or url:
            listing_id = url.split("/")[-1]
            listings.append(Property(listing_id=listing_id, price=price, location=location, url=url, lat=lat, lon=lon))

    return listings

def save_to_csv(listings: list[Property], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["listing_id", "price", "location", "url", "latitude", "longitude"])
        writer.writeheader()
        writer.writerows([listing.model_dump() for listing in listings])

print(f"Fetching {TARGET_URL} ...")
html = asyncio.run(fetch_html(TARGET_URL))

print("Parsing listing cards ...")
listings = parse_listings(html)
validated = PropertyList(listings=listings)

print(f"\n--- Found {len(validated.listings)} listing(s) ---")
print(json.dumps([l.model_dump() for l in validated.listings], indent=2, ensure_ascii=False))

save_to_csv(validated.listings, CSV_PATH)
print(f"\nSaved to {CSV_PATH}")