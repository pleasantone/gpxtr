# pylint: disable=missing-function-docstring,line-too-long
"""
create a markdown template from a Garmin GPX file for route information
"""

import argparse
import io
import math
from datetime import datetime
from typing import Optional, Union

import astral
import astral.sun
import geopandas as gpd
import gpxpy
import markdown2
import numpy as np
import pandas as pd

from gpxpy.gpx import GPXTrack, GPXWaypoint, GPXRoutePoint, GPXException
from gpxpy.geo import distance
from scipy.spatial import cKDTree
from shapely.geometry import Point

KM_TO_MILES = 0.621371
M_TO_FEET = 3.28084
NAMESPACE = {
    'trp':  'http://www.garmin.com/xmlschemas/TripExtensions/v1',
    'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
}

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
            return duration.text.replace('PT', '+').lower()
    return ''

def departure_time(point) -> Optional[datetime]:
    """ returns datetime object for route point with departure times or None """
    for extension in point.extensions:
        for departure in extension.findall('trp:DepartureTime', NAMESPACE):
            return datetime.fromisoformat(departure.text.replace('Z', '+00:00'))

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

def geodata_tracks(tracks: list[GPXTrack]) -> gpd.GeoDataFrame:
    tracks_points = []
    total_distance = 0.0
    for track in tracks:
        track_distance = 0.0
        last = track.segments[0].points[0]
        track_length = track.length_2d() / 1000. * KM_TO_MILES
        for segment in track.segments:
            for point in segment.points:
                delta = distance(last.latitude, last.longitude, None, point.latitude, point.longitude, None) / 1000 * KM_TO_MILES
                track_distance += delta
                total_distance += delta
                last = point
                tracks_points.append([Point(point.latitude, point.longitude),
                                    track_distance, total_distance, track_length])
    return gpd.GeoDataFrame(tracks_points,
                            columns=['geometry', 'track_distance', 'total_distance', 'track_length'],
                            crs="EPSG:4326") # type: ignore

def geodata_points(points: Union[list[GPXWaypoint], list[GPXRoutePoint]]) -> gpd.GeoDataFrame:
    waypoints = []
    for point in points:
        waypoints.append([Point(point.latitude, point.longitude),
                         point.name, point.symbol,
                         departure_time(point) or pd.NaT,
                         layover(point)])
    return gpd.GeoDataFrame(waypoints,
                            columns=['geometry', 'name', 'symbol', 'departure', 'layover'],
                            crs="EPSG:4326") # type: ignore

def geodata_nearest(points: gpd.GeoDataFrame, tracks: gpd.GeoDataFrame, sort=None) -> pd.DataFrame:
    np_points = np.array(list(points.geometry.apply(lambda x: (x.x, x.y))))
    np_tracks = np.array(list(tracks.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(np_tracks)
    dist, idx = btree.query(np_points, k=1)
    tracks_nearest = tracks.iloc[idx].drop(columns="geometry").reset_index(drop=True)
    dataframe = pd.concat(
        [
            points.reset_index(drop=True),
            tracks_nearest,
            pd.Series(dist, name='nearest')
        ],
        axis=1)
    return dataframe.sort_values(by=(sort or ['total_distance', 'name']))

def is_gas(point) -> str:
    if point.symbol and 'Gas Station' in point.symbol:
        return 'G'
    return ''

def waypoint_from_point(point, name, symbol=None):
    waypoint = GPXWaypoint()
    waypoint.latitude = point.latitude
    waypoint.longitude = point.longitude
    waypoint.name = name
    waypoint.symbol = symbol
    return waypoint

OUT_HDR = '|        Lat,Lon       | Name                           |   Dist. | G |  ETA  | Notes'
OUT_SEP = '| :------------------: | :----------------------------- | ------: | - | ----: | :----'
OUT_FMT = '| {:-10.4f},{:.4f} | {:30.30} | {:>7} | {:1} | {:>5} | {}{}'

def format_point(point, last_gas: float) -> str:
    departure = point.departure.to_pydatetime() if point.departure not in [pd.NaT, None] else None
    if last_gas > point.track_distance:   # assume we have filled up between segments
        last_gas = 0.0
    return OUT_FMT.format(
        point.geometry.x, point.geometry.y,
        (point.name or '').replace('\n', ' '),
        f'{round(point.track_distance - last_gas):.0f}/{round(point.track_distance):.0f}' if
            is_gas(point) or
            abs(point.track_distance - point.track_length) < 1.0 else f'{round(point.track_distance):.0f}',
        is_gas(point) or ' ',
        departure.astimezone().strftime('%H:%M') if departure else '',
        point.symbol or '',
        f' ({point.layover})' if point.layover else '')

def format_route_point(point: GPXRoutePoint, last_gas: float, dist: float, last_point: bool) -> str:
    departure = departure_time(point)
    lay = layover(point)
    if last_gas > dist:
        last_gas = 0.0
    return OUT_FMT.format(
        point.latitude, point.longitude,
        (point.name or '').replace('\n', ' '),
        f'{round(dist - last_gas):.0f}/{dist:.0f}' if is_gas(point) or last_point
            else f'{round(dist):.0f}',
        is_gas(point) or ' ',
        departure.astimezone().strftime('%H:%M') if departure else '',
        point.symbol or '',
        f' ({lay})' if lay else '')

def print_route_table(gpx, out=None) -> None:
    for route in gpx.routes:
        if route.name:
            print(f'## {route.name}', file=out)
        if route.description:
            print(f'- {route.description}', file=out)
        print(f'- {sun_rise_set(route)}', file=out)
        print(f'\n{OUT_HDR}\n{OUT_SEP}', file=out)
        dist = 0.0
        previous = route.points[0].latitude, route.points[0].longitude
        last_gas = 0.0
        for point in route.points:
            if not shaping_point(point):
                print(format_route_point(point, last_gas, dist, point is route.points[-1]), file=out)
            if is_gas(point):
                last_gas = dist
            current = point.latitude, point.longitude
            dist += distance(previous[0], previous[1], None, current[0], current[1], None) / 1000 * KM_TO_MILES
            for extension in point.extensions:
                for extension_point in extension.findall('gpxx:rpt', NAMESPACE):
                    current = float(extension_point.get('lat')), float(extension_point.get('lon'))
                    dist += distance(previous[0], previous[1], None, current[0], current[1], None) / 1000 * KM_TO_MILES
                    previous = current

def print_wpt_table(gpx, sort=None, out=None) -> None:
    for track in gpx.tracks:
#       gpx.waypoints.append(waypoint_from_point(track.segments[0].points[0], f'START: {track.name}', 'START'))
        gpx.waypoints.append(waypoint_from_point(track.segments[-1].points[-1], f'END: {track.name}', 'END'))

    if gpx.waypoints and gpx.tracks:
        gd_tracks = geodata_tracks(gpx.tracks)
        gd_waypoints = geodata_points(gpx.waypoints)
        gd_merged = geodata_nearest(gd_waypoints, gd_tracks, sort=sort)
        print('## Waypoints', file=out)
        print(f'\n{OUT_HDR}\n{OUT_SEP}', file=out)
        last_gas = 0.0
        for point in gd_merged.itertuples():
            print(format_point(point, last_gas), file=out)
            if is_gas(point):
                last_gas = point.track_distance

def print_gpx(gpx, sort=None, out=None) -> None:
    if gpx.name:
        print(f'# {gpx.name}', file=out)
    if gpx.creator:
        print(f'- {gpx.creator}', file=out)
    move_data = gpx.get_moving_data()
    if move_data and move_data.moving_time:
        print(f'- Total moving time: {format_time(move_data.moving_time, False)}', file=out)
    dist = gpx.length_2d()
    if dist:
        print(f'- Total distance: {format_long_length(dist, True)}', file=out)
    print_wpt_table(gpx, sort=sort, out=out)
    print_route_table(gpx)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="+", type=argparse.FileType('r'), help="input file(s)")
    parser.add_argument("--html", action='store_true', help="output in HTML, not markdown")
    parser.add_argument("--output", type=argparse.FileType('w'), default=None, help="output file")
    parser.add_argument("--sort", default=None, help="sort algorithm for waypoints (only)")
    args = parser.parse_args()

    out = args.output
    final_out = None
    if args.html:
        final_out = out
        out = io.StringIO()

    if args.sort:
        args.sort = args.sort.split(',')

    for handle in args.input:
        with handle as stream:
            try:
                print_gpx(gpxpy.parse(stream), sort=args.sort, out=out)
            except GPXException as err:
                raise SystemExit(f'{handle.name}: {err}') from err

    if args.html:
        print(markdown2.markdown(out.getvalue(), extras=["tables"]), file=final_out)
        if final_out:
            final_out.close()
    if out:
        out.close()

if __name__ == '__main__':
    main()
