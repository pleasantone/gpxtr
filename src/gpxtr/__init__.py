# pylint: disable=line-too-long, missing-function-docstring
"""
GPXtr - Create a markdown template from a Garmin GPX file for route information
"""

__version__ = "0.2.0"

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

from gpxpy.gpx import (
    GPX,
    GPXTrack,
    GPXWaypoint,
    GPXRoutePoint,
    GPXTrackPoint,
    GPXException,
)
from gpxpy.geo import distance
from scipy.spatial import cKDTree
from shapely.geometry import Point

KM_TO_MILES = 0.621371
M_TO_FEET = 3.28084
LAST_WAYPOINT_DELTA = 200.0  # 200m allowed between last waypoint and end of track


DEFAULT_TRAVEL_SPEED = 30.0 / KM_TO_MILES  #: 50kph or ~30mph
DEFAULT_WAYPOINT_DELAYS = {
    "Restaurant": timedelta(minutes=60),
    "Gas Station": timedelta(minutes=15),
    "Restroom": timedelta(minutes=15),
    "Photo": timedelta(minutes=5),
}  #: Add a layover time automatically if a symbol matches


OUT_HDR = "|        Lat,Lon       | Name                           |   Dist. | G |  ETA  | Notes"
OUT_SEP = "| :------------------: | :----------------------------- | ------: | - | ----: | :----"
OUT_FMT = "| {:-10.4f},{:.4f} | {:30.30} | {:>7} | {:1} | {:>5} | {}{}"

XML_NAMESPACE = {
    "trp": "http://www.garmin.com/xmlschemas/TripExtensions/v1",
    "gpxx": "http://www.garmin.com/xmlschemas/GpxExtensions/v3",
}


class GPXTableCalculator:
    """
    Create a waypoint/route-point table based upon GPX information.

    :param GPX gpx: gpxpy gpx data
    :param bool imperial: display in Imperial units (default metric)
    :param float speed: optional speed of travel for time-distance calculations
    :param datetime departure: if provided, departure time for route or tracks to start
    :param waypoint_delays: a non-default symbol-to-automatic waypoint delays dictionary (see DEFAULT_WAYPOINT_DELAYS)
    :type waypoint_delays: dict or None
    """

    def __init__(
        self,
        gpx: GPX,
        imperial: bool = True,
        speed: float = 0.0,
        departure: Optional[datetime] = None,
        waypoint_delays: Optional[dict] = None,
    ) -> None:
        self.gpx = gpx
        self.speed = (
            speed / KM_TO_MILES if imperial else speed
        ) or DEFAULT_TRAVEL_SPEED
        self.imperial = imperial
        self.depart_at = departure
        self.waypoint_delays = waypoint_delays or DEFAULT_WAYPOINT_DELAYS

    def print_header(self, out: Optional[io.TextIOWrapper] = None) -> None:
        """
        Print to stream generic information about the GPX data such as name, creator, and calculation
        variables.

        :param out: optional stream, otherwise standard output
        :type out: None or TextIOWrapper

        :return: nothing
        """
        if self.gpx.name:
            print(f"# {self.gpx.name}", file=out)
        if self.gpx.creator:
            print(f"- {self.gpx.creator}", file=out)
        move_data = self.gpx.get_moving_data()
        if move_data and move_data.moving_time:
            print(
                f"- Total moving time: {self.format_time(move_data.moving_time, False)}",
                file=out,
            )
        dist = self.gpx.length_2d()
        if dist:
            print(f"- Total distance: {self.format_long_length(dist, True)}", file=out)
        if self.speed:
            print(f"- Default speed: {self.format_speed(self.speed, True)}", file=out)

    def print_waypoints(
        self, sort: str = "", out: Optional[io.TextIOWrapper] = None
    ) -> None:
        """
        Print waypoint information

        Look for all the waypoints associated with tracks present to attempt to reconstruct
        the order and distance of the waypoints. If a departure time has been set, estimate
        the arrival time at each waypoint and probable layover times.

        :param sort: optional comma separate string for waypoint order.
                     May include 'track_distance', 'total_distance', 'name', and 'symbol'.
                     Defaults to the order waypoints appear in the file.
        :type sort: None or str
        :param out: optional stream, otherwise standard output
        :type out: None or TextIOWrapper

        :return: nothing
        """

        def _wpe() -> str:
            last_waypoint = (
                abs(point.track_distance - point.track_length) < LAST_WAYPOINT_DELTA
            )
            return OUT_FMT.format(
                point.geometry.x,
                point.geometry.y,
                (point.name or "").replace("\n", " "),
                f"{self.format_long_length(round(point.track_distance - last_gas))}/{self.format_long_length(round(point.track_distance))}"
                if self.is_gas(point) or last_waypoint
                else f"{self.format_long_length(round(point.track_distance))}",
                self.is_gas(point) or " ",
                departure.astimezone().strftime("%H:%M") if departure else "",
                point.symbol or "",
                f" (+{str(self.symbol_delay(point))[:-3]})"
                if not first_point and self.symbol_delay(point)
                else "",
            )

        for track in self.gpx.tracks:
            #       self.gpx.waypoints.append(_waypoint_from_point(track.segments[0].points[0],
            #            f'START: {track.name}', 'START'))
            self.gpx.waypoints.append(
                self.waypoint_from_point(
                    track.segments[-1].points[-1], f"END: {track.name}", "END"
                )
            )
        if self.gpx.waypoints and self.gpx.tracks:
            print(
                f"- {self.sun_rise_set(self.gpx.tracks[0].segments[0].points[0])}",
                file=out,
            )
            print("## Waypoints", file=out)
            print(f"\n{OUT_HDR}\n{OUT_SEP}", file=out)
            last_gas = 0.0
            start_time = self.depart_at
            first_point = True
            for point in self.geodata_nearest(
                self.geodata_points(self.gpx.waypoints),
                self.geodata_tracks(self.gpx.tracks),
                sort=sort,
            ).itertuples():
                departure = (
                    start_time + self.travel_time(point.track_distance)
                    if start_time
                    else None
                )
                if (
                    last_gas > point.track_distance
                ):  # assume we have filled up between segments
                    last_gas = 0.0
                print(_wpe(), file=out)
                if self.is_gas(point):
                    last_gas = point.track_distance
                delay = self.symbol_delay(point) if not first_point else None
                if delay and start_time:
                    start_time += delay
                first_point = False

    def print_routes(self, out: Optional[io.TextIOWrapper] = None) -> None:
        """
        Print route points present in GPX routes.

        If Garmin extensions to create "route-tracks" are present will calculate distances, arrival and departure
        times properly. If the route points have symbols encoded properly, will automatically compute layover
        estimates as well as gas stops.

        :param out: optional stream, otherwise standard output
        :type out: None or TextIOWrapper

        :return: nothing
        """

        def _rpe() -> str:
            return OUT_FMT.format(
                point.latitude,
                point.longitude,
                (point.name or "").replace("\n", " "),
                f"{self.format_long_length(dist - last_gas)}/{self.format_long_length(dist)}"
                if self.is_gas(point) or point is route.points[-1]
                else f"{self.format_long_length(dist)}",
                self.is_gas(point) or " ",
                timing.astimezone().strftime("%H:%M") if timing else "",
                point.symbol or "",
                f" (+{str(delay)[:-3]})" if delay else "",
            )

        for route in self.gpx.routes:
            print(f"\n## Route: {route.name}", file=out)
            if route.description:
                print(f"- {route.description}", file=out)
            print(f"- {self.sun_rise_set(route.points[0])}", file=out)
            print(f"\n{OUT_HDR}\n{OUT_SEP}", file=out)
            dist = 0.0
            previous = route.points[0].latitude, route.points[0].longitude
            last_gas = 0.0
            timing = self.departure_time(route.points[0]) or self.depart_at
            last_display_distance = 0.0
            for point in route.points:
                if not self.shaping_point(point):
                    if timing:
                        timing += self.travel_time(dist - last_display_distance)
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
                dist += distance(
                    previous[0], previous[1], None, current[0], current[1], None
                )
                for extension in point.extensions:
                    for extension_point in extension.findall("gpxx:rpt", XML_NAMESPACE):
                        current = float(extension_point.get("lat")), float(
                            extension_point.get("lon")
                        )
                        dist += distance(
                            previous[0], previous[1], None, current[0], current[1], None
                        )
                        previous = current
                previous = current

    @staticmethod
    def waypoint_from_point(
        point, name: str, symbol: Optional[str] = None
    ) -> GPXWaypoint:
        return GPXWaypoint(point.latitude, point.longitude, name=name, symbol=symbol)

    @staticmethod
    def geodata_tracks(tracks: list[GPXTrack]) -> gpd.GeoDataFrame:
        tracks_points = []
        total_distance = 0.0
        for track in tracks:
            track_distance = 0.0
            last = track.segments[0].points[0]
            track_length = track.length_2d()
            for segment in track.segments:
                for point in segment.points:
                    delta = distance(
                        last.latitude,
                        last.longitude,
                        None,
                        point.latitude,
                        point.longitude,
                        None,
                    )
                    track_distance += delta
                    total_distance += delta
                    last = point
                    tracks_points.append(
                        [
                            Point(point.latitude, point.longitude),
                            track_distance,
                            total_distance,
                            track_length,
                        ]
                    )
        return gpd.GeoDataFrame(
            tracks_points,
            columns=["geometry", "track_distance", "total_distance", "track_length"],
            crs="EPSG:4326",
        )  # type: ignore

    @staticmethod
    def geodata_points(
        points: Union[list[GPXWaypoint], list[GPXRoutePoint]]
    ) -> gpd.GeoDataFrame:
        waypoints = []
        for point in points:
            waypoints.append(
                [Point(point.latitude, point.longitude), point.name, point.symbol]
            )
        return gpd.GeoDataFrame(
            waypoints, columns=["geometry", "name", "symbol"], crs="EPSG:4326"
        )  # type: ignore

    @staticmethod
    def geodata_nearest(
        points: gpd.GeoDataFrame, tracks: gpd.GeoDataFrame, sort: str = ""
    ) -> pd.DataFrame:
        np_points = np.array(list(points.geometry.apply(lambda x: (x.x, x.y))))
        np_tracks = np.array(list(tracks.geometry.apply(lambda x: (x.x, x.y))))
        btree = cKDTree(np_tracks)
        dist, idx = btree.query(np_points, k=1)
        tracks_nearest = (
            tracks.iloc[idx].drop(columns="geometry").reset_index(drop=True)
        )
        dataframe = pd.concat(
            [
                points.reset_index(drop=True),
                tracks_nearest,
                pd.Series(dist, name="nearest"),
            ],
            axis=1,
        )
        if sort:
            dataframe = dataframe.sort_values(by=sort)
        return dataframe

    @staticmethod
    def format_time(time_s: float, seconds: bool) -> str:
        if not time_s:
            return "n/a"
        if seconds:
            return str(int(time_s))
        minutes = math.floor(time_s / 60.0)
        hours = math.floor(minutes / 60.0)
        return f"{int(hours):02d}:{int(minutes % 60):02d}:{int(time_s % 60):02d}"

    def format_long_length(self, length: float, units: bool = False) -> str:
        if self.imperial:
            return f'{round(length / 1000. * KM_TO_MILES):.0f}{" mi" if units else ""}'
        return f'{round(length / 1000.):.0f}{" km" if units else ""}'

    def format_short_length(self, length: float, units: bool = False) -> str:
        if self.imperial:
            return f'{length * M_TO_FEET:.2f}{" ft" if units else ""}'
        return f'{length:.2f}{" m" if units else ""}'

    def format_speed(self, speed: Optional[float], units: bool = False) -> str:
        """speed is in kph"""
        if not speed:
            speed = 0.0
        if self.imperial:
            return f'{speed * KM_TO_MILES:.2f}{" mph" if units else ""}'
        return f'{speed:.2f}{" km/h" if units else ""}'

    def symbol_delay(self, point: Union[GPXWaypoint, GPXRoutePoint]) -> timedelta:
        return self.waypoint_delays.get(point.symbol or "nil") or timedelta()

    def travel_time(self, dist: float) -> timedelta:
        """distance is in meters, speed is in km/h"""
        return timedelta(minutes=dist / 1000.0 / self.speed * 60.0)

    @staticmethod
    def layover(point: GPXRoutePoint) -> timedelta:
        """layover time at a given RoutePoint (Basecamp extension)"""
        for extension in point.extensions:
            for duration in extension.findall("trp:StopDuration", XML_NAMESPACE):
                match = re.match(r"^PT((\d+)H)?((\d+)M)?$", duration.text)
                if match:
                    return timedelta(
                        hours=int(match.group(2) or "0"),
                        minutes=int(match.group(4) or "0"),
                    )
        return timedelta()

    @staticmethod
    def departure_time(
        point: Union[GPXWaypoint, GPXRoutePoint, GPXTrackPoint]
    ) -> Optional[datetime]:
        """returns datetime object for route point with departure times or None"""
        for extension in point.extensions:
            for departure in extension.findall("trp:DepartureTime", XML_NAMESPACE):
                return datetime.fromisoformat(departure.text.replace("Z", "+00:00"))
        return None

    def sun_rise_set(
        self, point: Union[GPXWaypoint, GPXRoutePoint, GPXTrackPoint]
    ) -> str:
        """return sunrise/sunset info based upon the route start point"""
        start = astral.LocationInfo(
            "Start Point", "", "", point.latitude, point.longitude
        )
        sun = astral.sun.sun(
            start.observer, date=(self.departure_time(point) or self.depart_at)
        )
        return (
            f'Sunrise: {sun["sunrise"].astimezone():%H:%M}, '
            f'Sunset: {sun["sunset"].astimezone():%H:%M}'
        )

    @staticmethod
    def is_gas(point: Union[GPXWaypoint, GPXRoutePoint]) -> str:
        if (
            point.symbol
            and "Gas Station" in point.symbol
            or re.search(r"\bGas\b", point.name or "", re.I)
        ):
            return "G"
        return ""

    @staticmethod
    def shaping_point(point: Union[GPXWaypoint, GPXRoutePoint]) -> bool:
        """:return: True if route point is a shaping/Via point"""
        if not point.name:
            return True
        if point.name.startswith("Via "):
            return True
        for extension in point.extensions:
            if "ShapingPoint" in extension.tag:
                return True
        return False


class _DateParser(argparse.Action):
    """
    Argparse extension to support natural date parsing.

    Date string must be sent in complete so needs quoting on command line.
    :meta private:
    """

    def __call__(self, parser, namespace, values, option_strings=None):
        setattr(
            namespace,
            self.dest,
            dateutil.parser.parse(values, default=datetime.now(dateutil.tz.tzlocal())),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", nargs="+", type=argparse.FileType("r"), help="input file(s)"
    )
    parser.add_argument(
        "--output", type=argparse.FileType("w"), default=None, help="output file"
    )
    parser.add_argument(
        "--sort", default="", type=str, help="sort algorithm (for waypoints only)"
    )
    parser.add_argument(
        "--departure",
        default=None,
        action=_DateParser,
        help="set departure time for first point (local timezone)",
    )
    parser.add_argument(
        "--speed", default=0.0, type=float, help="set average travel speed"
    )
    parser.add_argument(
        "--html", action="store_true", help="output in HTML, not markdown"
    )
    parser.add_argument(
        "--metric", action="store_true", help="Use metric units (default imperial)"
    )

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
        args.sort = args.sort.split(",")

    for handle in args.input:
        with handle as stream:
            try:
                table = GPXTableCalculator(
                    gpxpy.parse(stream),
                    speed=args.speed,
                    departure=args.departure,
                    imperial=not args.metric,
                )
                table.print_header(out=out)
                table.print_waypoints(sort=args.sort, out=out)
                table.print_routes(out=out)
            except GPXException as err:
                raise SystemExit(f"{handle.name}: {err}") from err

    if args.html:
        print(markdown2.markdown(out.getvalue(), extras=["tables"]), file=final_out)
        if final_out:
            final_out.close()
    if out:
        out.close()


if __name__ == "__main__":
    main()
