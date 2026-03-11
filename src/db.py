import sqlite3
from pathlib import Path
from schema import Property

DB_PATH = Path(__file__).parent.parent / "data" / "properties.db"

def check_recent(country):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = '''
            SELECT listing_id
            FROM properties
            WHERE country = ?
            ORDER BY scraped_at DESC
            LIMIT 20;
        '''
        cursor.execute(query, (country,))
        return {row[0] for row in cursor.fetchall()}

def create_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT,
                location TEXT,
                country TEXT,
                price TEXT,
                property_type TEXT,
                bedrooms REAL,
                bathrooms REAL,
                toilet_rooms REAL,
                living_area TEXT,
                land_area TEXT,
                rooms REAL,
                parking REAL,
                construction_year INTEGER,
                lat TEXT,
                lon TEXT,
                distance_to_coast_km REAL,
                url TEXT UNIQUE,
                features TEXT,
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
            print(f"inserting values {values}")
            conn.execute(
                f"INSERT OR IGNORE INTO properties ({columns}) VALUES ({placeholders})",
                values
            )
        conn.commit()
