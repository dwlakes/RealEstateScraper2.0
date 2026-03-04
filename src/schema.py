from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
FIELD_MAP = {
    "Bedrooms": "bedrooms",
    "Bathrooms": "bathrooms",
    "Toilet rooms": "toilet_rooms",
    "Rooms": "rooms",
    "Type": "property_type",
    "lat": "lat",
    "lon": "lon",
    "Living area": "living_area",
    "Land": "land_area",
    "Parking lots (inside)": "parking",
    "Construction year": "construction_year",
}

class Property(BaseModel):
    model_config = ConfigDict(frozen=False)
    listing_id: str = ""
    location: str = ""
    country: str = ""
    price: str = ""
    property_type: str = ""
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    toilet_rooms: Optional[float] = None
    living_area: str = ""
    land_area: str = ""
    rooms: Optional[float] = None
    parking: Optional[float] = None
    construction_year: Optional[int] = None
    lat: str = ""
    lon: str = ""
    url: str = ""
    features: str = ""

class PropertyList(BaseModel):
    listings: List[Property]