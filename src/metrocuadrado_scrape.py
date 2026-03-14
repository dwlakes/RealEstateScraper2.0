import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from schema import Property
import db
import regex as re
import calc_distance
import random
import time
import requests
from pprint import pprint


EMPTY_CITIES = {
    "nearest_city_1k": "", "distance_to_city_1k_km": None,
    "nearest_city_50k": "", "distance_to_city_50k_km": None,
    "nearest_city_500k": "", "distance_to_city_500k_km": None,
    "nearest_city_1mil": "", "distance_to_city_1mil_km": None,
}

BASE_URL = "https://www.metrocuadrado.com"
house_types = ["casa", "apartamento", "casas-campestres", "casalote", "lote", "apartaestudio"]


async def fetch_listings_page(url: str) -> str:
    await asyncio.sleep(random.uniform(2, 5))
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
        await page.wait_for_selector(".property-list__container", timeout=10000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_selector(".property-list__container", timeout=5000)
        await asyncio.sleep(random.uniform(2, 5))
        html = await page.content()
        await browser.close()
    return html


def parse_property_info(prop):
    lat = str(prop['coordinates']['lat']) if prop.get('coordinates') else ""
    lon = str(prop['coordinates']['lon']) if prop.get('coordinates') else ""

    try:
        nearest_cities = calc_distance.nearest_city(lat, lon) or EMPTY_CITIES
    except Exception as e:
        print(f"Nearest city failed: {e}")
        nearest_cities = EMPTY_CITIES

    try:
        elevation = calc_distance.get_elevation(lat, lon) or {"elevation_m": None}
    except Exception as e:
        print(f"Elevation failed: {e}")
        elevation = {"elevation_m": None}

    try:
        dist2coast = calc_distance.distance_to_coast(lat, lon) or {"distance_to_coast_km": None}
    except Exception as e:
        print(f"Coast distance failed: {e}")
        dist2coast = {"distance_to_coast_km": None}

    return Property(
        listing_id=f"MC_{prop['propertyId']}",
        source_site="metrocuadrado.com",
        country="colombia",
        location=prop['city']['nombre'],
        price=str(prop['salePrice']),
        price_usd=None,
        price_currency="COP",
        bedrooms=float(prop['rooms']) if prop.get('rooms') else None,
        bathrooms=float(prop['bathrooms']) if prop.get('bathrooms') else None,
        m2=float(prop['area']) if prop.get('area') else None,
        property_type=prop['propertyType']['nombre'],
        lat=lat,
        lon=lon,
        is_project=1 if prop.get('isProject') else 0,
        stratum=int(prop['stratum']) if prop.get('stratum') else None,
        url=f"https://www.metrocuadrado.com{prop['detail']['urlDetail']}",
        **elevation, **dist2coast, **nearest_cities,
    )


def get_property_info(link_list, from_param):
    houses = []
    for link in link_list:
        print(f"Fetching {link}...")
        print(f"Page/from param: {from_param}")
        print(f"house type: {house_type}")
        try:
            time.sleep(random.uniform(2, 5))
            response = requests.get(link, timeout=10)
            response.encoding = "utf-8"
        except requests.exceptions.ReadTimeout:
            print(f"Timeout on {link}, retrying...")
            try:
                response = requests.get(link, timeout=30)
                response.encoding = "utf-8"
            except Exception as e:
                print(f"Retry failed for {link}: {e}")
                continue
        except Exception as e:
            print(f"Failed to fetch {link}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        script = None
        for tag in soup.find_all("script"):
            if tag.string and "propertyId" in tag.string:
                script = tag
                break

        if not script:
            print(f"No property data found for {link}")
            continue

        match = re.search(r'\[1,"(.*?)"\]\)', script.string, re.DOTALL)
        if not match:
            print(f"No match found for {link}")
            continue

        try:
            raw = match.group(1).encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
            idx = raw.find('"data":{"propertyId"')
            if idx < 0:
                print(f"No propertyId data block found for {link}")
                continue
            start = idx + len('"data":')
            data, _ = json.JSONDecoder().raw_decode(raw, start)
            house = parse_property_info(data)
            houses.append(house)
        except Exception as e:
            print(f"Failed to parse {link}: {e}")
            continue

    return houses


def scrape_type(house_type):
    from_param = 0
    duplicate_pages = 0

    while True:
        url = f"{BASE_URL}/{house_type}/venta/?search=form&from={from_param}"
        print(f"Fetching {url}...")
        html = asyncio.run(fetch_listings_page(url))
        soup = BeautifulSoup(html, "html.parser")

        cards = soup.find_all(class_="property-card__container")
        print(f"Found {len(cards)} cards on page from={from_param}")
        if not cards:
            print("No cards found, stopping.")
            break

        link_list = []
        for card in cards:
            link = card.find("a", href=True)
            href = link["href"] if link else ""
            if href:
                full_url = (BASE_URL + href) if href.startswith("/") else href
                link_list.append(full_url)

        listing_ids = [f"MC_{l.split('/')[-1].split('?')[0]}" for l in link_list]
        existing = db.listings_exist(listing_ids)

        if set(listing_ids).issubset(existing):
            duplicate_pages += 1
            print(f"Duplicate page {duplicate_pages}/3 for {house_type}")
            if duplicate_pages >= 3:
                print("3 consecutive duplicate pages, stopping.")
                break
            from_param += 20
            continue
        else:
            duplicate_pages = 0

        new_links = [l for l in link_list if f"MC_{l.split('/')[-1].split('?')[0]}" not in existing]
        houses = get_property_info(new_links, from_param)

        if houses:
            try:
                db.insert_properties(houses)
                print(f"Inserted {len(houses)} listings from from={from_param}")
            except Exception as e:
                print(f"DB insert failed: {e}")

        # check for next page
        next_btn = soup.find("button", {"aria-label": "next page"})
        if not next_btn or next_btn.get("disabled") is not None:
            print("No next page, stopping.")
            break

        from_param += 20
        time.sleep(random.uniform(2, 5))


db.create_db()
for house_type in house_types:
    scrape_type(house_type)