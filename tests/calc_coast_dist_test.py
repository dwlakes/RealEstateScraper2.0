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
from schema import Property, PropertyList, FIELD_MAP
from dist_to_coast import distance_to_coast
import db
import regex as re

# --- Paths ---
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "properstar_listings.csv"

BASE_URL = "https://www.properstar.com"

COUNTRIES = [
    "colombia",
    "mexico",
    "peru",
    "chile",
    "brazil",
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

        global getting_coords
        if getting_coords == True:
               print(f"getting coords is {getting_coords}")
               # Scroll to bottom to load map
               await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
               await page.wait_for_selector(".static-map-image", timeout=30000)
               await page.wait_for_selector(".location-map", timeout=30000) 
               getting_coords = False
               print(f"Getting coords is: {getting_coords}")
        html = await page.content()
        await browser.close()
    return html

def parse_listings(html: str, country: str) -> list[Property]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="items-list-small")
    if not container:
        print("WARNING — listing container not found")
        return []

    cards = container.find_all(class_=lambda c: c and ("card-full" in c or "card-extended" in c or "card-basic" in c))
    
    id_list = []
    for card in cards:
        link = card.find("a", href=True)
        href = link["href"] if link else ""
        url = (BASE_URL + href) if href.startswith("/") else href
        listing_id = url.split("/")[-1]
        id_list.append(listing_id)
    recent_listings = db.check_recent(country)
    # print(f"check recents: {recent_listings}")

    if set(id_list).issubset(recent_listings):
        print(f"All listings on this page already in DB, skipping {country}")
        return []
    else:
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

        prop_type_el = card.find(class_= "item-highlights")
        prop_type_list = (prop_type_el.get_text()).split("•") if loc_el else "" 
        prop_type = prop_type_list[0]

        listing_id = url.split("/")[-1]
          
        listings.append(Property(listing_id=listing_id, price=price, location=location, url=url, property_type=prop_type, country=country, source_site="properstar.com"))

    return listings

def get_coords(container):
    coords_regex = re.search(r'center=([-\d.]+)%2C([-\d.]+)', str(container))
    print(f"coords regex {coords_regex}")
    if not coords_regex:
        return{"lat":"", "lon":""}
    return {"lat": coords_regex.group(1), "lon":coords_regex.group(2)}


def parse_features(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="location-map")
    if not container:
        print("WARNING — location-map container not found")
    if container:
        #print(f"container {container}")
        coords = get_coords(container)
        print(f"lat {coords["lat"]}")
        print(f"lon {coords["lon"]}")
    if coords["lat"] == "" and coords["lon"] == "":
        print("No coordinates to calc distance")
    else:
        dist2coast = distance_to_coast(coords["lat"], coords["lon"])
        print(f"dist found: {dist2coast}")
    features = {}
    for item in soup.find_all(class_="feature-item"):
        key = item.find(class_="property-key")
        value = item.find(class_="property-value")
        if key and value:
            features[key.get_text(strip=True)] = value.get_text(strip=True)
            features.update(coords)
        
    return features

def save_to_csv(listings: list[Property], path: Path) -> None:
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(Property.model_fields.keys()))
        writer.writeheader()
        writer.writerows([listing.model_dump() for listing in listings])

global page
page = 2
def get_country_listings(country):
    global page, getting_coords
    TARGET_URL = f"{BASE_URL}/{country}/buy?p={page}"
    print(f"Fetching {TARGET_URL} ...")
    html = asyncio.run(fetch_html(TARGET_URL))

    print("Parsing listing cards ...")
    listings = parse_listings(html, country)
    validated = PropertyList(listings=listings)

    for house in validated.listings:
        getting_coords = True
        print(f"Getting coords is: {getting_coords}")
        html = asyncio.run(fetch_html(house.url))
        soup = BeautifulSoup(html, "html.parser")
        features = parse_features(html)
        for key, val in FIELD_MAP.items():
            if key in features and features[key] is not None:
                setattr(house, val, features[key])
        house.bedrooms = float(house.bedrooms) if house.bedrooms else None
        house.bathrooms = float(house.bathrooms) if house.bathrooms else None
        house.toilet_rooms = float(house.toilet_rooms) if house.toilet_rooms else None
        house.rooms = float(house.rooms) if house.rooms else None
        house.parking = float(house.parking) if house.parking else None
        print(f"url: {house.url}")
        print("--------New House--------")

    all_listings.extend(validated.listings)
    db.create_db()
    db.insert_property(all_listings)
    soup = BeautifulSoup(html, "html.parser")
    next_btn = soup.find("li", class_="page-link next")
    if not next_btn or next_btn.get("aria-disabled") == "true":
        print("No next button, moving on to next country.")
        page = 1
        return
    else:
        page = page+1
        print(f"Next page found. Moving on to page {page}")
    #save_to_csv(validated.listings, CSV_PATH)



all_listings = []

for country in COUNTRIES[4:5]:
    get_country_listings(country)
    

print(f"\n--- Found {len(all_listings)} total listing(s) ---")