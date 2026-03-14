import sqlite3
from pathlib import Path
from schema import Property
from pprint import pprint

DB_PATH = Path(__file__).parent.parent / "data" / "properties.db"

def check_recent(country, source_site):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT listing_id FROM properties WHERE country = ? AND source_site = ? ORDER BY scraped_at DESC LIMIT 20",
            (country, source_site)
        )
        return {row[0] for row in cursor.fetchall()}

def listings_exist(id_list: list) -> set:
    with sqlite3.connect(DB_PATH) as conn:
        placeholders = ",".join(["?" for _ in id_list])
        cursor = conn.execute(
            f"SELECT listing_id FROM properties WHERE listing_id IN ({placeholders})",
            id_list
        )
        return {row[0] for row in cursor.fetchall()}

def create_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT,
                location TEXT,
                source_site TEXT,
                country TEXT,
                price TEXT,
                price_usd REAL,
                price_currency TEXT,
                property_type TEXT,
                bedrooms REAL,
                bathrooms REAL,
                toilet_rooms REAL,
                living_area TEXT,
                land_area TEXT,
                m2 REAL,
                rooms REAL,
                parking REAL,
                construction_year INTEGER,
                stratum INTEGER,
                is_project INTEGER,
                lat TEXT,
                lon TEXT,
                distance_to_coast_km REAL,
                elevation_m REAL,
                nearest_city_1k TEXT,
                distance_to_city_1k_km REAL,
                nearest_city_50k TEXT,
                distance_to_city_50k_km REAL,
                nearest_city_500k TEXT,
                distance_to_city_500k_km REAL,
                nearest_city_1mil TEXT,
                distance_to_city_1mil_km REAL,
                url TEXT UNIQUE,
                features TEXT,
                last_seen TIMESTAMP,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("Table created")

def insert_properties(listings: list[Property]):
    with sqlite3.connect(DB_PATH) as conn:
        for listing in listings:
            data = listing.model_dump()
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            values = tuple(data.values())
            print("----------------inserting values to db----------------")
            pprint(values)
            conn.execute(
                f"INSERT OR IGNORE INTO properties ({columns}) VALUES ({placeholders})",
                values
            )
        conn.commit()

def update_last_seen(listing_ids: list):
    with sqlite3.connect(DB_PATH) as conn:
        placeholders = ",".join(["?" for _ in listing_ids])
        conn.execute(
            f"UPDATE properties SET last_seen = CURRENT_TIMESTAMP WHERE listing_id IN ({placeholders})",
            listing_ids
        )
        conn.commit()