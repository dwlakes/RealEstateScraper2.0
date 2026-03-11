import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path

coastline = gpd.read_file(Path(__file__).parent.parent / "data" / "ne_10m_coastline" / "ne_10m_coastline.shp")
coastline = coastline.to_crs("EPSG:3857") 

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

    # Convert to km and find shortest distance
    print(f"Dist: {distances.min()}")
    return distances.min()/1000


"""lat = ""
lon = ""
distance_to_coast(lat, lon)"""