import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from schema import Property, PropertyList
import db
import regex as re
import calc_distance
import random
from pprint import pprint

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
BASE_URL = "https://www.properstar.com"

COUNTRIES = [
    #"colombia",
    "mexico",
    "peru",
    "chile",
    "brazil", "venezuela",
    "puerto-rico", "dominican-republic", "nicaragua", "el-salvador",
    "honduras", "guatemala", "guyana", "french-guiana", "belize",
    "jamaica", "ecuador", "bolivia", "argentina", "paraguay",
    "uruguay", "costa-rica", "panama"
]

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
        html = await page.content()
        await asyncio.sleep(random.uniform(1, 3))
        await browser.close()
    return html

def parse_listings(html: str, country: str) -> list[str] | str:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="items-list-small")
    if not container:
        print("WARNING — listing container not found")
        return []

    cards = container.find_all(class_=lambda c: c and (
        "card-full" in c or "card-extended" in c or
        "card-basic" in c or "card-global" in c
    ))

    urls = []
    for card in cards:
        link = card.find("a", href=True)
        href = link["href"] if link else ""
        url = (BASE_URL + href) if href.startswith("/") else href
        if url:
            urls.append(url)

    id_list = [u.split("/")[-1] for u in urls]
    recent_listings = db.check_recent(country, "properstar.com")
    print(f"recents {recent_listings}")
    print(f"id list {id_list}")
    if id_list and set(id_list).issubset(recent_listings):
        print(f"All listings on this page already in DB {country}")
        return "duplicate"

    print(f"Found new listings for {country}")
    return urls

def parse_property_page(html: str, url: str, country: str) -> Property:
    listing_id = url.split("/")[-1]
    soup = BeautifulSoup(html, "html.parser")

    state = None
    for script in soup.find_all("script"):
        if script.string and "__INITIAL_STATE__" in script.string:
            raw = script.string.split("window.__INITIAL_STATE__ = ", 1)[1].rstrip(";")
            state = json.loads(raw)
            break

    if not state:
        raise ValueError(f"__INITIAL_STATE__ not found for {url}")
    listing = state["entities"]["listing"][listing_id]
    loc = listing.get("location", {})

    # Price
    price_vals = listing.get("price", {}).get("values", [])
    price_orig = next((v for v in price_vals if v.get("type") == "Original"), {})
    price_converted = next((v for v in price_vals if v.get("type") == "Converted"), {})

    orig_currency = price_orig.get("currencyId", "")
    orig_value = price_orig.get("value")

    if orig_currency == "USD":
        price_usd = float(orig_value) if orig_value is not None else None
    else:
        conv_value = price_converted.get("value")
        price_usd = float(conv_value) if conv_value is not None else None

    # Area
    area_vals = listing.get("area", {}).get("values", [])
    living_m2 = next((v for v in area_vals if v.get("unit", {}).get("id") == "SquareMeter"), {})

    # Parking: sum inside + outside
    number_of = listing.get("numberOf", {})
    parking_inside = number_of.get("parkingLotsInside") or 0
    parking_outside = number_of.get("parkingLotsOutside") or 0
    total_parking = parking_inside + parking_outside
    parking = float(total_parking) if total_parking else None

    # Coordinates
    lat = str(loc.get("latitude", ""))
    lon = str(loc.get("longitude", ""))

    # Geo calculations
    dist2coast = {"distance_to_coast_km": None}
    elevation = {"elevation_m": None}
    nearest_cities = {
        "nearest_city_1k": "", "distance_to_city_1k_km": None,
        "nearest_city_50k": "", "distance_to_city_50k_km": None,
        "nearest_city_500k": "", "distance_to_city_500k_km": None,
        "nearest_city_1mil": "", "distance_to_city_1mil_km": None,
    }
    
    if lat and lon:
        try:
            dist2coast = calc_distance.distance_to_coast(lat, lon)
        except Exception as e:
            print(f"Coast distance failed: {e}")
        try:
            result = calc_distance.get_elevation(lat, lon)
            elevation = result if result is not None else {"elevation_m": None}
        except Exception as e:
            print(f"Elevation failed: {e}")
        try:
            nearest_cities = calc_distance.nearest_city(lat, lon)
        except Exception as e:
            print(f"Nearest city failed: {e}")

    address_parts = [loc.get("address1", ""), loc.get("city", "")]
    location = ", ".join(p for p in address_parts if p)

    return Property(
        listing_id=listing_id,
        url=url,
        country=country,
        source_site="properstar.com",
        price=str(orig_value) if orig_value is not None else "",
        price_currency=orig_currency,
        price_usd=price_usd,
        property_type=listing.get("type", {}).get("id", ""),
        bedrooms=number_of.get("bedrooms"),
        bathrooms=number_of.get("bathrooms"),
        parking=parking,
        living_area=str(living_m2.get("living", "")) if living_m2 else "",
        land_area=str(living_m2.get("land", "")) if living_m2 else "",
        construction_year=listing.get("constructionYear"),
        lat=lat,
        lon=lon,
        location=location,
        distance_to_coast_km=dist2coast.get("distance_to_coast_km"),
        elevation_m=elevation.get("elevation_m"),
        nearest_city_1k=nearest_cities.get("nearest_city_1k", ""),
        distance_to_city_1k_km=nearest_cities.get("distance_to_city_1k_km"),
        nearest_city_50k=nearest_cities.get("nearest_city_50k", ""),
        distance_to_city_50k_km=nearest_cities.get("distance_to_city_50k_km"),
        nearest_city_500k=nearest_cities.get("nearest_city_500k", ""),
        distance_to_city_500k_km=nearest_cities.get("distance_to_city_500k_km"),
        nearest_city_1mil=nearest_cities.get("nearest_city_1mil", ""),
        distance_to_city_1mil_km=nearest_cities.get("distance_to_city_1mil_km"),
    )

def get_country_listings(country, page):
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

    urls = parse_listings(index_html, country)
    if urls == "duplicate":
        return "duplicate"

    listings = []
    for url in urls:
        print(f"page {page} country {country} url {url}")
        try:
            html = asyncio.run(fetch_html(url))
            prop = parse_property_page(html, url, country)
            print("--------------Property------------")
            pprint(prop)
            listings.append(prop)
        except Exception as e:
            print(f"Failed to process {url}: {e}")

    if listings:
        try:
            db.insert_properties(listings)
        except Exception as e:
            print(f"DB insert failed: {e}")

    index_soup = BeautifulSoup(index_html, "html.parser")
    next_btn = index_soup.find("li", class_="page-link next")
    if not next_btn or next_btn.get("aria-disabled") == "true":
        page = 1
        print("No next button, moving on to next country.")
        return "done"

    return "continue"


db.create_db()
page = 8
for country in COUNTRIES:
    #page = 1
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
