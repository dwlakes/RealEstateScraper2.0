from pydantic import BaseModel, ConfigDict
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
    "distance_to_coast_km": "distance_to_coast_km",
    "elevation_m": "elevation_m",
    "nearest_city_1k": "nearest_city_1k",
    "distance_to_city_1k_km": "distance_to_city_1k_km",
    "nearest_city_50k": "nearest_city_50k",
    "distance_to_city_50k_km": "distance_to_city_50k_km",
    "nearest_city_500k": "nearest_city_500k",
    "distance_to_city_500k_km": "distance_to_city_500k_km",
    "nearest_city_1mil": "nearest_city_1mil",
    "distance_to_city_1mil_km": "distance_to_city_1mil_km"
}


class Property(BaseModel):
    model_config = ConfigDict(frozen=False)
    listing_id: str = ""
    location: str = ""
    source_site: str = ""
    country: str = ""
    price: str = ""
    price_usd: Optional[float] = None
    price_currency: str = ""
    property_type: str = ""
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    toilet_rooms: Optional[float] = None
    living_area: str = ""
    land_area: str = ""
    m2: Optional[float] = None
    rooms: Optional[float] = None
    parking: Optional[float] = None
    construction_year: Optional[int] = None
    stratum: Optional[int] = None
    is_project: Optional[int] = None
    lat: str = ""
    lon: str = ""
    distance_to_coast_km: Optional[float] = None
    elevation_m: Optional[float] = None
    nearest_city_1k: str = ""
    distance_to_city_1k_km: Optional[float] = None
    nearest_city_50k: str = ""
    distance_to_city_50k_km: Optional[float] = None
    nearest_city_500k: str = ""
    distance_to_city_500k_km: Optional[float] = None
    nearest_city_1mil: str = ""
    distance_to_city_1mil_km: Optional[float] = None
    url: str = ""
    features: str = ""
    last_seen: Optional[str] = None

class PropertyList(BaseModel):
    listings: List[Property]