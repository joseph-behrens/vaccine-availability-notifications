from collections import defaultdict
from typing import Dict, List
import math

import zipcodes
from geopy.distance import geodesic
from geopy.units import meters
import pygeohash

from chalicelib.logs.decorators import func_time
from chalicelib.logs.utils import get_logger


logger = get_logger(__name__)

GEOHASH_PRECISION = 3


def get_zipcode_parent_geohash(zipcode: str) -> str:
    zipcode_info = zipcodes.matching(zipcode)[0]
    return pygeohash.encode(
        float(zipcode_info['lat']),
        float(zipcode_info['long']),
        GEOHASH_PRECISION,
    )


@func_time
def find_geohashes_in_radius(lat: float, long: float, radius_miles: int) -> List[str]:
    radius_meters = meters(miles=radius_miles)
    return list(create_geohash(lat, long, radius_meters, GEOHASH_PRECISION))


@func_time
def find_zipcode_distances(
    state_abbr: str,
    location_coordinates: List[int],
) -> dict:
    zipcode_distance_map: Dict[int, Dict[str, int]] = defaultdict(dict)

    state_zipcodes = zipcodes.filter_by(active=True, state=state_abbr)
    for zipcode_info in state_zipcodes:
        zipcode = zipcode_info["zip_code"]
        coordinates = [zipcode_info["lat"], zipcode_info["long"]]

        distance = geodesic(location_coordinates, coordinates).miles
        if distance <= 5:
            zipcode_distance_map[5][zipcode] = distance
        if distance <= 10:
            zipcode_distance_map[10][zipcode] = distance
        if distance <= 25:
            zipcode_distance_map[25][zipcode] = distance
        if distance <= 50:
            zipcode_distance_map[50][zipcode] = distance

    return zipcode_distance_map


def in_circle_check(latitude, longitude, centre_lat, centre_lon, radius):
    x_diff = longitude - centre_lon
    y_diff = latitude - centre_lat

    if math.pow(x_diff, 2) + math.pow(y_diff, 2) <= math.pow(radius, 2):
        return True

    return False


def get_centroid(latitude, longitude, height, width):
    y_cen = latitude + (height / 2)
    x_cen = longitude + (width / 2)

    return x_cen, y_cen


def convert_to_latlon(y, x, latitude, longitude):
    pi = 3.14159265359

    r_earth = 6371000

    lat_diff = (y / r_earth) * (180 / pi)
    lon_diff = (x / r_earth) * (180 / pi) / math.cos(latitude * pi/180)

    final_lat = latitude+lat_diff
    final_lon = longitude+lon_diff

    return final_lat, final_lon


def create_geohash(latitude: float, longitude: float, radius: int, precision):
    x = 0.0
    y = 0.0

    points = []
    geohashes = []

    grid_width = [5009400.0, 1252300.0, 156500.0, 39100.0, 4900.0, 1200.0, 152.9, 38.2, 4.8, 1.2, 0.149, 0.0370]
    grid_height = [4992600.0, 624100.0, 156000.0, 19500.0, 4900.0, 609.4, 152.4, 19.0, 4.8, 0.595, 0.149, 0.0199]

    height = (grid_height[precision - 1])/2
    width = (grid_width[precision-1])/2

    lat_moves = int(math.ceil(radius / height))
    lon_moves = int(math.ceil(radius / width))

    for i in range(0, lat_moves):

        temp_lat = y + height*i

        for j in range(0, lon_moves):

            temp_lon = x + width*j

            if in_circle_check(temp_lat, temp_lon, y, x, radius):

                x_cen, y_cen = get_centroid(temp_lat, temp_lon, height, width)

                lat, lon = convert_to_latlon(y_cen, x_cen, latitude, longitude)
                points += [[lat, lon]]
                lat, lon = convert_to_latlon(-y_cen, x_cen, latitude, longitude)
                points += [[lat, lon]]
                lat, lon = convert_to_latlon(y_cen, -x_cen, latitude, longitude)
                points += [[lat, lon]]
                lat, lon = convert_to_latlon(-y_cen, -x_cen, latitude, longitude)
                points += [[lat, lon]]

    for point in points:
        geohashes += [pygeohash.encode(point[0], point[1], precision)]

    return set(geohashes)