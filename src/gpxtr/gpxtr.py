# pylint: disable=missing-function-docstring,line-too-long
"""
create a markdown template from a Garmin GPX file for route information
"""

import argparse
import io
import math
import re
from datetime import datetime, timedelta
from typing import Optional, Union

import astral
import astral.sun
import dateutil.parser
import dateutil.tz
import geopandas as gpd
import gpxpy
import markdown2
import numpy as np
import pandas as pd

from gpxpy.gpx import GPX, GPXTrack, GPXWaypoint, GPXRoutePoint, GPXException
from gpxpy.geo import distance
from scipy.spatial import cKDTree
from shapely.geometry import Point


class GPXCalculator:
    OUT_HDR = '|        Lat,Lon       | Name                           |   Dist. | G |  ETA  | Notes'
    OUT_SEP = '| :------------------: | :----------------------------- | ------: | - | ----: | :----'
    OUT_FMT = '| {:-10.4f},{:.4f} | {:30.30} | {:>7} | {:1} | {:>5} | {}{}'

    KM_TO_MILES = 0.621371
    M_TO_FEET = 3.28084
    XML_NAMESPACE = {
        'trp':  'http://www.garmin.com/xmlschemas/TripExtensions/v1',
        'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
    }

    DEFAULT_TRAVEL_SPEED = 30.0 # mph
    DEFAULT_WAYPOINT_DELAYS = {
        "Restaurant":   timedelta(minutes=60),
        "Gas Station":  timedelta(minutes=15),
        "Restroom":     timedelta(minutes=15),
        "Photo":        timedelta(minutes=5)
    }

    def __init__(self, gpx: GPX, miles=True, speed=None, departure=None, waypoint_delays=None) -> None:
        self.gpx = gpx
        self.speed = speed or self.DEFAULT_TRAVEL_SPEED
        self.miles = miles
        self.depart_at = departure
        self.waypoint_delays = waypoint_delays or self.DEFAULT_WAYPOINT_DELAYS

    def print_header(self, out=None) -> None:
        if self.gpx.name:
            print(f'# {self.gpx.name}', file=out)
        if self.gpx.creator:
            print(f'- {self.gpx.creator}', file=out)
        move_data = self.gpx.get_moving_data()
        if move_data and move_data.moving_time:
            print(f'- Total moving time: {self.format_time(move_data.moving_time, False)}', file=out)
        dist = self.gpx.length_2d()
        if dist:
            print(f'- Total distance: {self.format_long_length(dist)}', file=out)

    def symbol_delay(self, point: Union[GPXWaypoint, GPXRoutePoint]) -> timedelta:
        return self.waypoint_delays.get(point.symbol or 'nil') or timedelta()

    def print_waypoints(self, sort=None, out=None) -> None:
        def _wpe() -> str:
            return self.OUT_FMT.format(
                point.geometry.x, point.geometry.y,
                (point.name or '').replace('\n', ' '),
                f'{round(point.track_distance - last_gas):.0f}/{round(point.track_distance):.0f}' if
                    self.is_gas(point) or
                    abs(point.track_distance - point.track_length) < 1.0 else f'{round(point.track_distance):.0f}',
                self.is_gas(point) or ' ',
                departure.astimezone().strftime('%H:%M') if departure else '',
                point.symbol or '',
                f' (+{str(self.symbol_delay(point))[:-3]})' if not first_point else '')

        def _waypoint_from_point(point, name, symbol=None):
            return GPXWaypoint(point.latitude, point.longitude, name=name, symbol=symbol)

        def geodata_tracks(tracks: list[GPXTrack]) -> gpd.GeoDataFrame:
            tracks_points = []
            total_distance = 0.0
            for track in tracks:
                track_distance = 0.0
                last = track.segments[0].points[0]
                track_length = track.length_2d() / 1000. * self.KM_TO_MILES
                for segment in track.segments:
                    for point in segment.points:
                        delta = distance(last.latitude, last.longitude, None,
                                        point.latitude, point.longitude, None) / 1000 * self.KM_TO_MILES
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
                                point.name, point.symbol])
            return gpd.GeoDataFrame(waypoints,
                                    columns=['geometry', 'name', 'symbol'],
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
            if sort:
                dataframe = dataframe.sort_values(by=sort)
            return dataframe

        for track in self.gpx.tracks:
    #       self.gpx.waypoints.append(_waypoint_from_point(track.segments[0].points[0],
    #            f'START: {track.name}', 'START'))
            self.gpx.waypoints.append(_waypoint_from_point(track.segments[-1].points[-1],
                f'END: {track.name}', 'END'))
        if self.gpx.waypoints and self.gpx.tracks:
            print('## Waypoints', file=out)
            print(f'\n{self.OUT_HDR}\n{self.OUT_SEP}', file=out)
            last_gas = 0.0
            start_time = self.depart_at
            first_point = True
            for point in geodata_nearest(geodata_points(self.gpx.waypoints),
                                         geodata_tracks(self.gpx.tracks), sort=sort).itertuples():
                departure = start_time + timedelta(minutes=point.track_distance * 60.0 / self.speed) if start_time else None
                if last_gas > point.track_distance:   # assume we have filled up between segments
                    last_gas = 0.0
                print(_wpe(), file=out)
                if self.is_gas(point):
                    last_gas = point.track_distance
                delay = self.symbol_delay(point) if not first_point else None
                if delay and start_time:
                    start_time += delay
                first_point = False

    def print_routes(self, out=None):
        def _rpe() -> str:
            return self.OUT_FMT.format(
                point.latitude, point.longitude,
                (point.name or '').replace('\n', ' '),
                f'{round(dist - last_gas):.0f}/{dist:.0f}' if self.is_gas(point) or point is route.points[-1]
                    else f'{round(dist):.0f}',
                self.is_gas(point) or ' ',
                timing.astimezone().strftime('%H:%M') if timing else '',
                point.symbol or '',
                f' (+{str(delay)[:-3]})' if delay else '')

        for route in self.gpx.routes:
            print(f'\n## Route: {route.name}', file=out)
            if route.description:
                print(f'- {route.description}', file=out)
            print(f'- {self.sun_rise_set(route.points[0])}', file=out)
            print(f'\n{self.OUT_HDR}\n{self.OUT_SEP}', file=out)
            dist = 0.0
            previous = route.points[0].latitude, route.points[0].longitude
            last_gas = 0.0
            timing = self.departure_time(route.points[0]) or self.depart_at
            last_display_distance = 0.0
            for point in route.points:
                if not self.shaping_point(point):
                    if timing:
                        timing += timedelta(minutes=(dist - last_display_distance) * (60.0 / self.speed))
                    last_display_distance = dist
                    departure = self.departure_time(point)
                    if departure:
                        timing = departure
                    delay = self.layover(point)
                    if last_gas > dist:
                        last_gas = 0.0
                    print(_rpe(), file=out)
                    if timing:
                        timing += delay
                if self.is_gas(point):
                    last_gas = dist
                current = point.latitude, point.longitude
                dist += distance(previous[0], previous[1], None,
                                 current[0], current[1], None) / 1000 * self.KM_TO_MILES
                for extension in point.extensions:
                    for extension_point in extension.findall('gpxx:rpt', self.XML_NAMESPACE):
                        current = float(extension_point.get('lat')), float(extension_point.get('lon'))
                        dist += distance(previous[0], previous[1], None,
                                         current[0], current[1], None) / 1000 * self.KM_TO_MILES
                        previous = current
                previous = current

    @staticmethod
    def format_time(time_s: float, seconds: bool) -> str:
        if not time_s:
            return 'n/a'
        if seconds:
            return str(int(time_s))
        minutes = math.floor(time_s / 60.)
        hours = math.floor(minutes / 60.)
        return f'{int(hours):02d}:{int(minutes % 60):02d}:{int(time_s % 60):02d}'

    def format_long_length(self, length: float) -> str:
        if self.miles:
            return f'{length / 1000. * self.KM_TO_MILES:.2f} mi'
        return f'{length/ 1000.:.2f} km'

    def format_short_length(self, length: float) -> str:
        if self.miles:
            return f'{length * self.M_TO_FEET:.2f} ft'
        return f'{length:.2f} m'

    def format_speed(self, speed: float) -> str:
        if not speed:
            speed = 0
        if self.miles:
            return f'{speed * self.KM_TO_MILES * 3600. / 1000.:.2f} mph'
        return f'{speed:.2f}m/s = {speed * 3600. / 1000.:.2f} km/h'

    def layover(self, point: GPXRoutePoint) -> timedelta:
        """ layover time at a given RoutePoint (Basecamp extension) """
        for extension in point.extensions:
            for duration in extension.findall('trp:StopDuration', self.XML_NAMESPACE):
                match = re.match(r'^PT((\d+)H)?((\d+)M)?$', duration.text)
                if match:
                    return timedelta(hours=int(match.group(2) or '0'), minutes=int(match.group(4) or '0'))
        return timedelta()

    def departure_time(self, point: Union[GPXWaypoint, GPXRoutePoint]) -> Optional[datetime]:
        """ returns datetime object for route point with departure times or None """
        for extension in point.extensions:
            for departure in extension.findall('trp:DepartureTime', self.XML_NAMESPACE):
                return datetime.fromisoformat(departure.text.replace('Z', '+00:00'))
        return None

    def sun_rise_set(self, point: Union[GPXWaypoint, GPXRoutePoint]) -> str:
        """ return sunrise/sunset info based upon the route start point """
        start = astral.LocationInfo("Start Point", "", "", point.latitude, point.longitude)
        sun = astral.sun.sun(start.observer, date=self.departure_time(point))
        return (f'Sunrise: {sun["sunrise"].astimezone():%H:%M}, '
                f'Sunset: {sun["sunset"].astimezone():%H:%M}')

    @staticmethod
    def is_gas(point) -> str:
        if point.symbol and 'Gas Station' in point.symbol:
            return 'G'
        return ''

    @staticmethod
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


class DateParser(argparse.Action):
    def __call__(self, parser, namespace, values, option_strings=None):
        setattr(namespace, self.dest, dateutil.parser.parse(values, default=datetime.now(dateutil.tz.tzlocal())))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="+", type=argparse.FileType('r'), help="input file(s)")
    parser.add_argument("--html", action='store_true', help="output in HTML, not markdown")
    parser.add_argument("--output", type=argparse.FileType('w'), default=None, help="output file")
    parser.add_argument("--sort", default=None, help="sort algorithm for waypoints (only)")
    parser.add_argument("--departure", default=None, action=DateParser, help="set departure time for first point")
    parser.add_argument("--speed", default=None, type=float, help="set average travel speed")

    try:
        args = parser.parse_args()
    except ValueError as err:
        raise SystemExit(err) from err

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
                table = GPXCalculator(gpxpy.parse(stream))
                table.depart_at = args.departure
                if args.speed:
                    table.speed = args.speed
                table.print_header(out=out)
                table.print_waypoints(sort=args.sort, out=out)
                table.print_routes(out=out)
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
