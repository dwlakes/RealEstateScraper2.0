import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from pathlib import Path
import json
import requests
import sys
from pprint import pprint

cities_file = Path(__file__).parent.parent / "data" / "cities1000.txt"
cities_df = pd.read_csv(
    cities_file,
    sep="\t",
    header=None,
    usecols=[1, 4, 5, 14],
    names=["name", "latitude", "longitude", "population"],
    low_memory=False
)

cities = gpd.GeoDataFrame(
    cities_df,
    geometry=gpd.points_from_xy(cities_df.longitude, cities_df.latitude),
    crs="EPSG:4326"
).to_crs("EPSG:3857")
cities_1k = cities  # already filtered by download
cities_50k = cities[cities_df["population"] > 50000]
cities_500k = cities[cities_df["population"] > 500000]
cities_1mil = cities[cities_df["population"] > 1000000]

coastline = gpd.read_file(Path(__file__).parent.parent / "data" / "ne_10m_coastline" / "ne_10m_coastline.shp")
coastline = coastline.to_crs("EPSG:3857") 

ELEVATION_APIS = [
    lambda lat, lon: requests.get(
        f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}",
        timeout=10
    ).json()["results"][0]["elevation"],
    lambda lat, lon: requests.get(
        f"https://api.opentopodata.org/v1/srtm90m?locations={lat},{lon}",
        timeout=10
    ).json()["results"][0]["elevation"],
    lambda lat, lon: requests.get(
        f"https://api.opentopodata.org/v1/aster30m?locations={lat},{lon}",
        timeout=10
    ).json()["results"][0]["elevation"],
]

api_fail_counts = [0, 0, 0]
FAIL_THRESHOLD = 3


def nearest_city(lat, lon):
    point = gpd.GeoDataFrame(
    geometry=[Point(float(lon), float(lat))],
    crs="EPSG:4326"
    ).to_crs("EPSG:3857").geometry[0]
    city_tiers = {
    "1k": cities_1k,
    "50k": cities_50k,
    "500k": cities_500k,
    "1mil": cities_1mil,
    }

    result = {}
    for tier, gdf in city_tiers.items():
        distances = gdf.geometry.distance(point)
        idx = distances.idxmin()
        result[f"nearest_city_{tier}"] = gdf.loc[idx]["name"]
        result[f"distance_to_city_{tier}_km"] = round(distances.min() / 1000, 3)
    pprint(result)
    return result


def get_elevation(lat, lon):
    for i, api in enumerate(ELEVATION_APIS):
        if api_fail_counts[i] >= FAIL_THRESHOLD:
            continue
        try:
            elevation = api(lat, lon)
            api_fail_counts[i] = 0  # reset on success
            return {"elevation_m": elevation}
        except Exception as e:
            api_fail_counts[i] += 1
            print(f"Elevation API {i+1} failed ({api_fail_counts[i]}): {e}")
    return {"elevation_m": None}

def distance_to_coast(lat, lon):
    print(f"Find distance to coast for {lat}, {lon}")
    point = Point(lon, lat)
    point_gdf = gpd.GeoDataFrame(geometry=[point], crs = "EPSG:4326")
    point_projected = point_gdf.to_crs("EPSG:3857")
    distances = coastline.geometry.distance(point_projected.geometry[0])
    nearest_idx = distances.idxmin()
    nearest_point = coastline.geometry[nearest_idx].interpolate(
        coastline.geometry[nearest_idx].project(point_projected.geometry[0])
    )
    nearest_wgs84 = gpd.GeoDataFrame(geometry=[nearest_point], crs="EPSG:3857").to_crs("EPSG:4326")
    print(f"Nearest coast point: {nearest_wgs84.geometry[0].y}, {nearest_wgs84.geometry[0].x}")
    coast_dict = {"distance_to_coast_km":distances.min()/1000}
    # Convert to km and find shortest distance
    #print(f"Dist: {distances.min()}")
    return coast_dict


"""lat = ""
lon = ""
distance_to_coast(lat, lon)"""

