import sqlite3
from pathlib import Path
from schema import Property


DB_PATH = Path(__file__).parent.parent / "data" / "properties.db"

def create_db():

    try:
        with sqlite3.connect(DB_PATH) as conn:
            print(f"Opened SQLite database with version {sqlite3.sqlite_version} successfully.")
            cursor = conn.cursor()

            create_table= """
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
        url TEXT UNIQUE,
        features TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    """
            cursor.execute(create_table)
            print("Table created")

    except sqlite3.OperationalError as e:
        print("Failed to open database:", e)

def insert_property(listings: list[Property]):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            print(f"Opened SQLite database with version {sqlite3.sqlite_version} successfully.")
            cursor = conn.cursor()
            for listing in listings:
                data = listing.model_dump()
                columns = ", ".join(data.keys())
                entry_placeholders = ", ".join(["?" for _ in data])
                values = tuple(data.values())
                cursor.execute(f"INSERT OR IGNORE INTO properties ({columns}) VALUES ({entry_placeholders})",
        values)

    except sqlite3.OperationalError as e:
        print("Failed to open database:", e)