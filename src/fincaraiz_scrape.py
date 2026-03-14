import requests
from bs4 import BeautifulSoup
import json
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from schema import Property
import calc_distance
import db
import time
import random

EMPTY_CITIES = {
    "nearest_city_1k": "", "distance_to_city_1k_km": None,
    "nearest_city_50k": "", "distance_to_city_50k_km": None,
    "nearest_city_500k": "", "distance_to_city_500k_km": None,
    "nearest_city_1mil": "", "distance_to_city_1mil_km": None,
}


def get_info(href):
    try:
        try:
            time.sleep(random.uniform(2, 5))
            response = requests.get(f"https://www.fincaraiz.com.co{href}", timeout=10)
        except requests.exceptions.ReadTimeout:
            print(f"Timeout on {href}, retrying...")
            response = requests.get(f"https://www.fincaraiz.com.co{href}", timeout=30)

        soup = BeautifulSoup(response.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            print(f"No __NEXT_DATA__ found for {href}")
            return None

        prop = json.loads(script.string)["props"]["pageProps"]["data"]

        lat = prop.get('latitude')
        lon = prop.get('longitude')

        if not lat or not lon:
            ld_script = soup.find("script", type="application/ld+json")
            if ld_script:
                ld_data = json.loads(ld_script.string)
                lat = ld_data.get("object", {}).get("geo", {}).get("latitude")
                lon = ld_data.get("object", {}).get("geo", {}).get("longitude")

        elevation = calc_distance.get_elevation(lat, lon) or {"elevation_m": None}
        dist2coast = calc_distance.distance_to_coast(lat, lon) or {"distance_to_coast_km": None}
        nearest_cities = calc_distance.nearest_city(lat, lon) or EMPTY_CITIES

        return Property(
            listing_id=f"FIN_{prop['id']}",
            source_site="fincaraiz.com.co",
            country="colombia",
            location=prop['locations']['city'][0]['name'] if prop['locations']['city'] else "",
            price=str(prop['price']['amount']),
            price_usd=prop['price_amount_usd'],
            price_currency=prop['price']['currency']['name'],
            bedrooms=prop['bedrooms'],
            bathrooms=prop['bathrooms'],
            m2=prop['m2'],
            property_type=prop['property_type']['name'],
            lat=str(lat) if lat else "",
            lon=str(lon) if lon else "",
            is_project=1 if prop['isProject'] else 0,
            stratum=prop.get('stratum'),
            url=f"https://www.fincaraiz.com.co{href}",
            **elevation,
            **dist2coast,
            **nearest_cities,
        )
    except Exception as e:
        print(f"Failed to process {href}: {e}")
        traceback.print_exc()
        return None


def scrape_type(house_type):
    page = 1
    duplicate_pages = 0
    while True:
        url = (
            f"https://www.fincaraiz.com.co/venta/{house_type}"
            if page == 1
            else f"https://www.fincaraiz.com.co/venta/{house_type}/pagina{page}"
        )
        print(f"Fetching {url}...")
        try:
            response = requests.get(url, timeout=10)
        except requests.exceptions.ReadTimeout:
            print(f"Timeout on {url}, retrying...")
            try:
                response = requests.get(url, timeout=30)
            except Exception as e:
                print(f"Retry failed, skipping page {page}: {e}")
                page += 1
                continue
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            page += 1
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        listings_wrapper = soup.find(class_="listingsWrapper")
        if not listings_wrapper:
            print("No listing wrapper found, stopping.")
            break

        hrefs = []
        for card in listings_wrapper.find_all(class_="listingBoxCard"):
            link = card.find("a", href=True)
            href = link["href"] if link else ""
            if href:
                hrefs.append(href)

        listing_ids = [f"FIN_{href.split('/')[-1]}" for href in hrefs]
        existing = db.listings_exist(listing_ids)

        if set(listing_ids).issubset(existing):
            duplicate_pages += 1
            print(f"Duplicate page {duplicate_pages}/3 for {house_type}")
            if duplicate_pages >= 3:
                print(f"3 consecutive duplicate pages, moving to next type.")
                break
            page += 1
            continue
        else:
            duplicate_pages = 0

        houses = []
        for href in hrefs:
            listing_id = f"FIN_{href.split('/')[-1]}"
            if listing_id in existing:
                print(f"Skipping existing listing {listing_id}")
                continue
            try:
                house = get_info(href)
                if house:
                    houses.append(house)
            except Exception as e:
                print(f"Failed to process card: {e}")

        try:
            db.insert_properties(houses)
            print(f"Inserted {len(houses)} listings from page {page}")
        except Exception as e:
            print(f"DB insert failed: {e}")

        next_page = soup.find("a", href=lambda h: h and f"venta/{house_type}/pagina{page + 1}" in h)
        if not next_page:
            print("No next page found, stopping.")
            break

        page += 1
        time.sleep(random.uniform(2, 5))


db.create_db()
house_types = ["casas", "apartamento", "casas-campestres", "casas-lotes", "lotes", "apartaestudios"]
for house_type in house_types:
    scrape_type(house_type)