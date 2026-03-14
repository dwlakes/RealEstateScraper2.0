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
    await asyncio.sleep(random.uniform(1, 3))
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
        
        """# click through to the right page
        for _ in range(page_num - 1):
            next_btn = await page.query_selector("button[aria-label='next page']")
            if not next_btn:
                break
            await next_btn.click()
            await page.wait_for_timeout(2000)"""
        
        # wait for cards to render
        await page.wait_for_selector(".property-list__container", timeout=10000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_selector(".property-list__container", timeout=5000)
        await asyncio.sleep(random.uniform(1, 3))
        html = await page.content()
        await browser.close()
    return html

def parse_property_info(info):
    prop = info
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
    lat=str(prop['coordinates']['lat']) if prop.get('coordinates') else "",
    lon=str(prop['coordinates']['lon']) if prop.get('coordinates') else "",
    is_project=1 if prop.get('isProject') else 0,
    stratum=int(prop['stratum']) if prop.get('stratum') else None,
    url=f"https://www.metrocuadrado.com{prop['detail']['urlDetail']}",
    # **elevation, **dist2coast, **nearest_cities,
)

def get_property_info(linkList):
    house_dict = {}
    for link in linkList:
        print("------------------Listing Page--------------------")
        print(f"Fetching {link}...")
        try:
            response = requests.get(link, timeout=10)
            response.encoding = "utf-8"
        except requests.exceptions.ReadTimeout:
            print(f"Timeout on {url}, retrying...")

        soup = BeautifulSoup(response.text, "html.parser")
         # find the script tag with the listing data
        script = None
        for tag in soup.find_all("script"):
            if tag.string and "propertyId" in tag.string:
                script = tag
                break
        if not script:
            print(f"No property data found for {url}")
            return None
        # extract JSON from the push call
        match = re.search(r'\[1,"(.*?)"\]\)', script.string, re.DOTALL)
        if not match:
            return None
        raw = match.group(1).encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
        idx = raw.find('"data":{"propertyId"')
        if idx < 0:
            print(f"No propertyId data block found for {link}")
            continue
        start = idx + len('"data":')
        data, _ = json.JSONDecoder().raw_decode(raw, start)
        house_data = parse_property_info(data)
        pprint(house_data)
        # navigate to the property data
        # pprint(data) to inspect structure first


        
        
        #html = asyncio.run(fetch_listings_page(link))
        #soup = BeautifulSoup(html, "html.parser")

for house_type in house_types[:1]:
    search_link = f"{BASE_URL}/{house_type}/venta/?search=form"
    html = asyncio.run(fetch_listings_page(search_link))
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all(class_="property-card__container")
    print(f"Found {len(cards)} cards")
    if not cards:
        print("No ad cards found")
    else:
        link_list = []
        for card in cards:
            link = card.find("a", href=True)
            href = link["href"] if link else ""
            url = (BASE_URL + href) if href.startswith("/") else href
            #print(url)
            link_list.append(url)
        houses = get_property_info(link_list)
    """main_results_list = soup.find(class_="property-list__results")
    if not main_results_list:
        print("no main list found")
    else:
        cardsx = soup.find_all("property-card__container")
        print(f"new cards found {len(cardsx)}")
     """


