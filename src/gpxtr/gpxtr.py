"""
create a markdown template from a Garmin GPX file for route information
"""

import argparse
import math
from datetime import datetime
from typing import Optional

import astral
import astral.sun
import geopandas as gpd
import gpxpy
import gpxpy.gpx
import numpy as np
import pandas as pd

from haversine import haversine, Unit
from scipy.spatial import cKDTree, distance
from shapely.geometry import Point

NAMESPACE = {
    'trp': 'http://www.garmin.com/xmlschemas/TripExtensions/v1'
}

# pylint: disable=line-too-long
OUT_HDR = '|      Lat,Lon       | Description                    |  Miles | Gas  | Time  | Layover | Notes'
OUT_SEP = '| :----------------: | :----------------------------- | -----: | :--: | ----: | ------: | :----'
OUT_FMT = '| {:-8.4f},{:.4f} | {:30.30} | {:6.2f} | {:>4} | {:>5} | {:>7} | {}'

KM_TO_MILES = 0.621371
M_TO_FEET = 3.28084


def format_time(time_s: float, seconds: bool) -> str:
    if not time_s:
        return 'n/a'
    if seconds:
        return str(int(time_s))
    minutes = math.floor(time_s / 60.)
    hours = math.floor(minutes / 60.)
    return f'{int(hours):02d}:{int(minutes % 60):02d}:{int(time_s % 60):02d}'

def format_long_length(length: float, miles: bool) -> str:
    if miles:
        return f'{length / 1000. * KM_TO_MILES:.2f} mi'
    return f'{length/ 1000.:.2f} km'

def format_short_length(length: float, miles: bool) -> str:
    if miles:
        return f'{length * M_TO_FEET:.2f} ft'
    return f'{length:.2f} m'

def format_speed(speed: float, miles: bool) -> str:
    if not speed:
        speed = 0
    if miles:
        return f'{speed * KM_TO_MILES * 3600. / 1000.:.2f} mph'
    return f'{speed:.2f}m/s = {speed * 3600. / 1000.:.2f} km/h'

def shaping_point(point) -> bool:
    """ is a route point just a shaping/Via point? """
    if not point.name:
        return True
    if point.name.startswith('Via '):
        return True
    for extension in point.extensions:
        if 'ShapingPoint' in extension.tag:
            return True
    return False

def layover(point) -> str:
    """ layover time at a given RoutePoint (Basecamp extension) """
    for extension in point.extensions:
        for duration in extension.findall('trp:StopDuration', NAMESPACE):
            return(duration.text.replace('PT', '+').lower())
    return ''

def departure_time(point) -> Optional[datetime]:
    """ returns datetime object for route point with departure times or None """
    for extension in point.extensions:
        for departure in extension.findall('trp:DepartureTime', NAMESPACE):
            return(datetime.fromisoformat(departure.text.replace('Z', '+00:00')))

def start_point(route) -> tuple[float, float, Optional[datetime]]:
    """ what is the start location of the route, and what's the departure time? """
    for point in route.points:
        return(point.latitude, point.longitude, departure_time(point))
    return (0.0, 0.0, None)

def sun_rise_set(route) -> str:
    """ return sunrise/sunset info based upon the route start point """
    lat, lon, start_date = start_point(route)
    start = astral.LocationInfo("Start Point", "", "", lat, lon)
    sun = astral.sun.sun(start.observer, date=start_date)
    return (f'Sunrise: {sun["sunrise"].astimezone():%H:%M}, '
            f'Sunset: {sun["sunset"].astimezone():%H:%M}')

def closest_node(node, nodes):
    closest_index = distance.cdist([node], nodes).argmin()
    return nodes[closest_index]

def geodata_tracks(tracks):
    track_points = []
    track_totals = 0.0
    for track in tracks:
        print(f'## Track {track.name})')
        segment_totals = 0.0
        last = track.segments[0].points[0]
        for segment in track.segments:
            for point in segment.points:
                delta = haversine((last.latitude, last.longitude), (point.latitude, point.longitude), Unit.MILES)
                segment_totals += delta
                track_totals += delta
                last = point
                track_points.append([Point(point.latitude, point.longitude), segment_totals, track_totals])
    return gpd.GeoDataFrame(track_points, columns=['geometry', 'segment_distance', 'total_distance'], crs="EPSG:4326")

def geodata_waypoints(points):
    waypoints = []
    for point in points:
        waypoints.append([Point(point.latitude, point.longitude), point.name, point.symbol])
    return gpd.GeoDataFrame(waypoints, columns=['geometry', 'name', 'symbol'], crs="EPSG:4326")

def geodata_merge_points(points, tracks):
    np_points = np.array(list(points.geometry.apply(lambda x: (x.x, x.y))))
    np_tracks = np.array(list(tracks.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(np_tracks)
    dist, idx = btree.query(np_points, k=1)
    tracks_nearest = tracks.iloc[idx].drop(columns="geometry").reset_index(drop=True)
    return pd.concat(
        [
            points.reset_index(drop=True),
            tracks_nearest,
            pd.Series(dist, name='dist')
        ],
        axis=1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input filename")
    args = parser.parse_args()

    with open(args.input, 'r', encoding='UTF-8') as file:
        gpx = gpxpy.parse(file)

    if gpx.name:
        print(f'# {gpx.name}')
    if gpx.creator:
        print(f'## {gpx.creator}')

    gd_tracks = geodata_tracks(gpx.tracks)
    gd_waypoints = geodata_waypoints(gpx.waypoints)
    gd_merged = geodata_merge_points(gd_waypoints, gd_tracks)
    print(gd_merged)

    print('\n## Waypoints')
    print(f'\n{OUT_HDR}\n{OUT_SEP}')
    for point in gd_merged.itertuples():
        print(OUT_FMT.format(
            point.geometry.x, point.geometry.y,
            (point.name or '').replace('\n', ' '),
            point.segment_distance,
            'G' if point.symbol and 'Gas Station' in point.symbol or point.Index == 0 else '',
            '',
            '',
            point.symbol or ''))

    for route in gpx.routes:
        if route.name:
            print(f'## {route.name}')
        if route.description:
            print(f'### {route.description}')
        print(f'\n{OUT_HDR}\n{OUT_SEP}')
        stop = 0
        for point in route.points:
            if not shaping_point(point):
                stop += 1
                departure = departure_time(point)
                print(OUT_FMT.format(
                    point.latitude, point.longitude,
                    (point.name or '').replace('\n', ' '),
                    0.0,
                    'G' if point.symbol and 'Gas Station' in point.symbol or stop == 1 else '',
                    departure.astimezone().strftime('%H:%M') if departure else '',
                    layover(point) or '',
                    point.symbol or ''))
        print(f'\n- {sun_rise_set(route)}')

    move_data = gpx.get_moving_data()
    if move_data and move_data.moving_time:
        print(f'- Total moving time: {format_time(move_data.moving_time, False)}')
    print(f'- Total distance: {format_long_length(gpx.length_2d(), True)}')
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
