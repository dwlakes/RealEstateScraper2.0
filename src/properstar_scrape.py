import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from schema import Property, PropertyList, FIELD_MAP
import db
import regex as re
import calc_distance
import random
import time

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
BASE_URL = "https://www.properstar.com"

COUNTRIES = [
    "colombia", "mexico", "peru", "chile", "brazil", "venezuela",
    "puerto-rico", "dominican-republic", "nicaragua", "el-salvador",
    "honduras", "guatemala", "guyana", "french-guiana", "belize",
    "jamaica", "ecuador", "bolivia", "argentina", "paraguay",
    "uruguay", "costa-rica", "panama"
]

getting_coords = False

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
        await asyncio.sleep(random.uniform(1, 3))
        global getting_coords
        if getting_coords:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_selector(".location-map", timeout=5000)
            getting_coords = False
        html = await page.content()
        await asyncio.sleep(random.uniform(1, 3))
        await browser.close()
    return html

def parse_listings(html: str, country: str) -> list[Property]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="items-list-small")
    if not container:
        print("WARNING — listing container not found")
        return []

    cards = container.find_all(class_=lambda c: c and (
        "card-full" in c or "card-extended" in c or
        "card-basic" in c or "card-global" in c
    ))

    id_list = []
    for card in cards:
        link = card.find("a", href=True)
        href = link["href"] if link else ""
        url = (BASE_URL + href) if href.startswith("/") else href
        id_list.append(url.split("/")[-1])

    recent_listings = db.check_recent(country, "properstar.com")
    print(f"recents {recent_listings}")
    print(f"id list {id_list}")
    if set(id_list).issubset(recent_listings):
        print(f"All listings on this page already in DB {country}")
        return "duplicate"

    print(f"Found new listings for {country}")
    listings = []
    for card in cards:
        link = card.find("a", href=True)
        href = link["href"] if link else ""
        url = (BASE_URL + href) if href.startswith("/") else href
        price_el = card.find(class_="listing-price-main")
        price = price_el.get_text(strip=True) if price_el else ""
        loc_el = card.find(class_="item-location")
        location = loc_el.get_text(separator=" ", strip=True) if loc_el else ""
        prop_type_el = card.find(class_="item-highlights")
        prop_type_list = prop_type_el.get_text().split("•") if prop_type_el else [""]
        listings.append(Property(
            listing_id=url.split("/")[-1],
            price=price,
            location=location,
            url=url,
            property_type=prop_type_list[0],
            country=country,
            source_site="properstar.com"
        ))
    return listings

def get_coords(container):
    coords_regex = re.search(r'center=([-\d.]+)%2C([-\d.]+)', str(container))
    if not coords_regex:
        return {"lat": "", "lon": ""}
    return {"lat": coords_regex.group(1), "lon": coords_regex.group(2)}

def parse_features(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    coords = {"lat": "", "lon": ""}
    dist2coast = {"distance_to_coast_km": None}
    elevation = {"elevation_m": None}
    nearest_cities = {
        "nearest_city_1k": "", "distance_to_city_1k_km": None,
        "nearest_city_50k": "", "distance_to_city_50k_km": None,
        "nearest_city_500k": "", "distance_to_city_500k_km": None,
        "nearest_city_1mil": "", "distance_to_city_1mil_km": None,
    }
    container = soup.find(class_="location-map")
    if not container:
        print("WARNING — location-map container not found")
    else:
        coords = get_coords(container)
        print(f"coords {coords}")
        if coords["lat"] and coords["lon"]:
            try:
                dist2coast = calc_distance.distance_to_coast(coords["lat"], coords["lon"])
            except Exception as e:
                print(f"Coast distance failed: {e}")
            try:
                elevation = calc_distance.get_elevation(coords["lat"], coords["lon"])
                if elevation is None:
                    elevation = {"elevation_m": None}
            except Exception as e:
                print(f"Elevation failed: {e}")
            try:
                nearest_cities = calc_distance.nearest_city(coords["lat"], coords["lon"])
            except Exception as e:
                print(f"Nearest city failed: {e}")

    features = {}
    for item in soup.find_all(class_="feature-item"):
        key = item.find(class_="property-key")
        value = item.find(class_="property-value")
        if key and value:
            features[key.get_text(strip=True)] = value.get_text(strip=True)
    features.update({**coords, **elevation, **nearest_cities, **dist2coast})
    return features

def get_country_listings(country, page):
    global getting_coords
    TARGET_URL = f"{BASE_URL}/{country}/buy?p={page}"
    print(f"Fetching {TARGET_URL} ...")
    try:
        index_html = asyncio.run(fetch_html(TARGET_URL))
    except Exception as e:
        print(f"Failed to fetch {TARGET_URL}: {e}, retrying...")
        try:
            index_html = asyncio.run(fetch_html(TARGET_URL))
        except Exception as e:
            print(f"Retry failed, skipping page {page} for {country}: {e}")
            return "error"

    listings = parse_listings(index_html, country)
    if listings == "duplicate":
        return "duplicate"

    validated = PropertyList(listings=listings)
    for house in validated.listings:
        print(f"page {page} country {country}")
        try:
            getting_coords = True
            html = asyncio.run(fetch_html(house.url))
            features = parse_features(html)
            for key, val in FIELD_MAP.items():
                if key in features and features[key] is not None:
                    setattr(house, val, features[key])
            house.bedrooms = float(house.bedrooms) if house.bedrooms else None
            house.bathrooms = float(house.bathrooms) if house.bathrooms else None
            house.toilet_rooms = float(house.toilet_rooms) if house.toilet_rooms else None
            house.rooms = float(house.rooms) if house.rooms else None
            house.parking = float(house.parking) if house.parking else None
            house.construction_year = int(house.construction_year) if house.construction_year else None
        except Exception as e:
            print(f"Failed to process {house.url}: {e}")

    try:
        db.insert_properties(validated.listings)
    except Exception as e:
        print(f"DB insert failed: {e}")

    index_soup = BeautifulSoup(index_html, "html.parser")
    next_btn = index_soup.find("li", class_="page-link next")
    if not next_btn or next_btn.get("aria-disabled") == "true":
        print("No next button, moving on to next country.")
        return "done"

    return "continue"


db.create_db()
for country in COUNTRIES:
    page = 1
    duplicate_pages = 0
    while True:
        result = get_country_listings(country, page)
        if result == "done":
            break
        elif result == "duplicate":
            duplicate_pages += 1
            print(f"Duplicate page {duplicate_pages}/3 for {country}")
            if duplicate_pages >= 3:
                print(f"3 consecutive duplicate pages, moving to next country.")
                break
            page += 1
        elif result == "error":
            page += 1
        else:  # continue
            duplicate_pages = 0
            page += 1