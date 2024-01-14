# pylint: disable=line-too-long, missing-function-docstring
"""
GPXtr - Create a markdown template from a Garmin GPX file for route information
"""

__version__ = "0.5.0"

import argparse
import io
import math
import re
import sys
from datetime import datetime, timedelta
from typing import Optional, Union, List, NamedTuple

import astral
import astral.sun
import dateutil.parser
import dateutil.tz
import gpxpy.gpx
import gpxpy.geo
import gpxpy.utils
import markdown2


KM_TO_MILES = 0.621371
M_TO_FEET = 3.28084

DEFAULT_LAST_WAYPOINT_DELTA = (
    200.0  # 200m allowed between last waypoint and end of track
)
DEFAULT_WAYPOINT_DEBOUNCE = (
    2000.0  # 2km between duplicates of the same waypoint on a track
)
DEFAULT_TRAVEL_SPEED = 30.0 / KM_TO_MILES  #: 50kph or ~30mph
DEFAULT_WAYPOINT_DELAYS = {
    "Restaurant": timedelta(minutes=60),
    "Gas Station": timedelta(minutes=15),
    "Restroom": timedelta(minutes=15),
    "Photo": timedelta(minutes=5),
    "Scenic Area": timedelta(minutes=5),
}  #: Add a layover time automatically if a symbol matches

LLP_HDR = "|        Lat,Lon       "
LLP_SEP = "| :------------------: "
LLP_FMT = "| {:-10.4f},{:.4f} "
OUT_HDR = "| Name                           |   Dist. | G |  ETA  | Notes"
OUT_SEP = "| :----------------------------- | ------: | - | ----: | :----"
OUT_FMT = "| {:30.30} | {:>7} | {:1} | {:>5} | {}{}"

XML_NAMESPACE = {
    "trp": "http://www.garmin.com/xmlschemas/TripExtensions/v1",
    "gpxx": "http://www.garmin.com/xmlschemas/GpxExtensions/v3",
}


class NearestLocationDataExt(NamedTuple):
    """
    Extended class for gpxpy.gpx.NearestLocationData

    Includes distance_from_start
    """

    location: "gpxpy.gpx.GPXTrackPoint"
    track_no: int
    segment_no: int
    point_no: int
    distance_from_start: float


class GPXTrackExt(gpxpy.gpx.GPXTrack):
    """
    Extended class for gpxpy.gpx.GPXTrack

    usage: ext_track = GPXTrackExt(track)
    """

    def __init__(self, track):  # pylint: disable=super-init-not-called
        self.gpx_track = track

    def get_points_data(self, distance_2d: bool = False) -> List[gpxpy.gpx.PointData]:
        """
        Returns a list of tuples containing the actual point, its distance from the start,
        track_no, segment_no, and segment_point_no
        """
        distance_from_start = 0.0
        previous_point = None

        # (point, distance_from_start) pairs:
        points = []

        for segment_no, segment in enumerate(self.gpx_track.segments):
            for point_no, point in enumerate(segment.points):
                if previous_point and point_no > 0:
                    if distance_2d:
                        distance = point.distance_2d(previous_point)
                    else:
                        distance = point.distance_3d(previous_point)

                    distance_from_start += distance or 0.0

                points.append(
                    gpxpy.gpx.PointData(
                        point, distance_from_start, -1, segment_no, point_no
                    )
                )

                previous_point = point

        return points

    def get_nearest_locations(
        self,
        location: gpxpy.geo.Location,
        threshold_distance: float = 0.01,
        deduplicate_distance: float = 0.0,
    ) -> List[NearestLocationDataExt]:
        """
        Returns a list of locations of elements like
        consisting of points where the location may be on the track

        threshold_distance is the minimum distance from the track
        so that the point *may* be counted as to be "on the track".
        For example 0.01 means 1% of the track distance.

        deduplicate_distance is an actual distance in meters, not a
        ratio based upon threshold. 2000 means it will not return
        duplicates within 2km in case the track wraps around itself.
        """

        def _deduplicate(
            locations: List[NearestLocationDataExt], delta: float = 0.0
        ) -> List[NearestLocationDataExt]:
            previous: Optional[NearestLocationDataExt] = None
            filtered: List[NearestLocationDataExt] = []
            for point in locations:
                if (
                    not previous
                    or (point.distance_from_start - previous.distance_from_start)
                    > delta
                ):
                    filtered.append(point)
                previous = point
            return filtered

        assert location
        assert threshold_distance

        result: List[NearestLocationDataExt] = []

        points = self.get_points_data()

        if not points:
            return result

        distance: Optional[float] = points[-1][1]

        threshold = (distance or 0.0) * threshold_distance

        min_distance_candidate: Optional[float] = None
        distance_from_start_candidate: Optional[float] = None
        track_no_candidate: Optional[int] = None
        segment_no_candidate: Optional[int] = None
        point_no_candidate: Optional[int] = None
        point_candidate: Optional[gpxpy.gpx.GPXTrackPoint] = None

        for point, distance_from_start, track_no, segment_no, point_no in points:
            distance = location.distance_3d(point) or math.inf
            if distance < threshold:
                if min_distance_candidate is None or distance < min_distance_candidate:
                    min_distance_candidate = distance
                    distance_from_start_candidate = distance_from_start
                    track_no_candidate = track_no
                    segment_no_candidate = segment_no
                    point_no_candidate = point_no
                    point_candidate = point
            else:
                if (
                    distance_from_start_candidate is not None
                    and point_candidate is not None
                    and track_no_candidate is not None
                    and segment_no_candidate is not None
                    and point_no_candidate is not None
                ):
                    result.append(
                        NearestLocationDataExt(
                            point_candidate,
                            track_no_candidate,
                            segment_no_candidate,
                            point_no_candidate,
                            distance_from_start_candidate,
                        )
                    )
                min_distance_candidate = None
                distance_from_start_candidate = None
                track_no_candidate = None
                segment_no_candidate = None
                point_no_candidate = None
                point_candidate = None

        if (
            distance_from_start_candidate is not None
            and point_candidate is not None
            and track_no_candidate is not None
            and segment_no_candidate is not None
            and point_no_candidate is not None
        ):
            result.append(
                NearestLocationDataExt(
                    point_candidate,
                    track_no_candidate,
                    segment_no_candidate,
                    point_no_candidate,
                    distance_from_start_candidate,
                )
            )
        return _deduplicate(result, deduplicate_distance)


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
        gpx: gpxpy.gpx.GPX,
        imperial: bool = True,
        speed: float = 0.0,
        depart_at: Optional[datetime] = None,
    ) -> None:
        self.gpx = gpx
        self.speed = (
            speed / KM_TO_MILES if imperial else speed
        ) or DEFAULT_TRAVEL_SPEED
        self.imperial = imperial
        self.depart_at = depart_at
        self.display_coordinates = False
        self.waypoint_delays = DEFAULT_WAYPOINT_DELAYS
        self.waypoint_debounce = DEFAULT_WAYPOINT_DEBOUNCE
        self.last_waypoint_delta = DEFAULT_LAST_WAYPOINT_DELTA

    def print_header(self) -> None:
        """
        Print to stream generic information about the GPX data such as name, creator, and calculation
        variables.

        :param out: optional stream, otherwise standard output
        :type out: None or TextIOWrapper

        :return: nothing
        """
        if self.gpx.name:
            print(f"## {self.gpx.name}")
        if self.gpx.creator:
            print(f"* {self.gpx.creator}")
        if self.depart_at:
            print(f"* Departure at {self.depart_at:%c}")
        move_data = self.gpx.get_moving_data()
        if move_data and move_data.moving_time:
            print(
                f"* Total moving time: {self.format_time(move_data.moving_time, False)}",
            )
        dist = self.gpx.length_2d()
        if dist:
            print(f"* Total distance: {self.format_long_length(dist, True)}")
        if self.speed:
            print(f"* Default speed: {self.format_speed(self.speed, True)}")

    def _populate_times(self) -> None:
        for track_no, track in enumerate(self.gpx.tracks):
            if self.depart_at and self.speed:
                if not track.has_times():
                    # assume (for now) that if there are multiple tracks, 1 track = 1 day
                    depart_at = self.depart_at + timedelta(hours=24 * track_no)
                    track.segments[0].points[0].time = depart_at
                    track.segments[-1].points[-1].time = depart_at + timedelta(
                        hours=track.length_2d() / (self.speed * 1000)
                    )
        self.gpx.add_missing_times()

    def print_waypoints(self) -> None:
        """
        Print waypoint information

        Look for all the waypoints associated with tracks present to attempt to reconstruct
        the order and distance of the waypoints. If a departure time has been set, estimate
        the arrival time at each waypoint and probable layover times.

        :param out: optional stream, otherwise standard output
        :type out: None or TextIOWrapper

        :return: nothing
        """

        def _wpe() -> str:
            final_waypoint = (
                abs(track_point.distance_from_start - track_length)
                < self.last_waypoint_delta
            )
            result = ""
            if self.display_coordinates:
                result += LLP_FMT.format(waypoint.latitude, waypoint.longitude)
            return result + OUT_FMT.format(
                (waypoint.name or "").replace("\n", " "),
                f"{self.format_long_length(round(track_point.distance_from_start - last_gas))}/{self.format_long_length(round(track_point.distance_from_start))}"
                if self.is_gas(waypoint) or final_waypoint
                else f"{self.format_long_length(round(track_point.distance_from_start))}",
                self.point_marker(waypoint),
                (track_point.location.time + waypoint_delays)
                .astimezone()
                .strftime("%H:%M")
                if track_point.location.time
                else "",
                waypoint.symbol or "",
                f" (+{str(layover)[:-3]})" if layover else "",
            )

        self._populate_times()
        for track in self.gpx.tracks:
            waypoints = [
                (
                    wp,
                    GPXTrackExt(track).get_nearest_locations(
                        wp, 0.001, deduplicate_distance=self.waypoint_debounce
                    ),
                )
                for wp in self.gpx.waypoints
            ]
            waypoints = sorted(
                [(wp, tp) for wp, tps in waypoints for tp in tps],
                key=lambda entry: entry[1].point_no,
            )
            track_length = track.length_2d()

            print(f"\n## Track: {track.name}")
            if track.description:
                print(f"* {track.description}")
            print(self._format_output_header())
            waypoint_delays = timedelta()
            last_gas = 0.0

            for waypoint, track_point in waypoints:
                first_waypoint = waypoint == waypoints[0][0]
                last_waypoint = waypoint == waypoints[-1][0]
                if last_gas > track_point.distance_from_start:
                    last_gas = 0.0  # assume we have filled up between track segments
                layover = (
                    timedelta()
                    if first_waypoint or last_waypoint
                    else self.point_delay(waypoint)
                )
                print(_wpe())
                if self.is_gas(waypoint):
                    last_gas = track_point.distance_from_start
                waypoint_delays += layover
            print(
                f"\n* {self.sun_rise_set(track.segments[0].points[0], track.segments[-1].points[-1], delay=waypoint_delays)}",
            )

    def print_routes(self) -> None:
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
            result = ""
            if self.display_coordinates:
                result += LLP_FMT.format(point.latitude, point.longitude)
            return result + OUT_FMT.format(
                (point.name or "").replace("\n", " "),
                f"{self.format_long_length(dist - last_gas)}/{self.format_long_length(dist)}"
                if self.is_gas(point) or point is route.points[-1]
                else f"{self.format_long_length(dist)}",
                self.point_marker(point),
                timing.astimezone().strftime("%H:%M") if timing else "",
                point.symbol or "",
                f" (+{str(delay)[:-3]})" if delay else "",
            )

        for route in self.gpx.routes:
            print(f"\n## Route: {route.name}")
            if route.description:
                print(f"* {route.description}")

            print(self._format_output_header())
            dist = 0.0
            previous = route.points[0].latitude, route.points[0].longitude
            last_gas = 0.0
            timing = self.departure_time(route.points[0], True)
            if timing:
                route.points[0].time = timing
            last_display_distance = 0.0
            for point in route.points:
                if not self.shaping_point(point):
                    if timing:
                        timing += self.travel_time(dist - last_display_distance)
                    last_display_distance = dist
                    departure = self.departure_time(point, dist == 0.0)
                    if departure:
                        timing = departure
                    delay = self.layover(point)
                    if last_gas > dist:
                        last_gas = 0.0
                    print(_rpe())
                    if timing:
                        timing += delay
                if self.is_gas(point):
                    last_gas = dist
                current = point.latitude, point.longitude
                dist += gpxpy.geo.distance(
                    previous[0], previous[1], None, current[0], current[1], None
                )
                for extension in point.extensions:
                    for extension_point in extension.findall("gpxx:rpt", XML_NAMESPACE):
                        current = float(extension_point.get("lat")), float(
                            extension_point.get("lon")
                        )
                        dist += gpxpy.geo.distance(
                            previous[0], previous[1], None, current[0], current[1], None
                        )
                        previous = current
                previous = current
            if timing:
                route.points[-1].time = timing
            print(
                f"\n- {self.sun_rise_set(route.points[0], route.points[-1])}",
            )

    def _format_output_header(self) -> str:
        if self.display_coordinates:
            return f"\n{LLP_HDR}{OUT_HDR}\n{LLP_SEP}{OUT_SEP}"
        return f"\n{OUT_HDR}\n{OUT_SEP}"

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

    def point_delay(
        self, point: Union[gpxpy.gpx.GPXWaypoint, gpxpy.gpx.GPXRoutePoint]
    ) -> timedelta:
        return (
            (
                self.waypoint_delays.get("Restaurant")
                if self.is_meal(point)
                else timedelta()
            )
            or (
                self.waypoint_delays.get("Gas Station")
                if self.is_gas(point)
                else timedelta()
            )
            or (
                self.waypoint_delays.get("Scenic Area")
                if self.is_scenic_area(point)
                else timedelta()
            )
            or self.waypoint_delays.get(point.symbol or "nil")
            or timedelta()
        )

    def point_marker(
        self, point: Union[gpxpy.gpx.GPXWaypoint, gpxpy.gpx.GPXRoutePoint]
    ) -> str:
        return (
            self.is_meal(point)
            or self.is_gas(point)
            or self.is_scenic_area(point)
            or " "
        )

    def travel_time(self, dist: float) -> timedelta:
        """distance is in meters, speed is in km/h"""
        return timedelta(minutes=dist / 1000.0 / self.speed * 60.0)

    @staticmethod
    def layover(point: gpxpy.gpx.GPXRoutePoint) -> timedelta:
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

    def departure_time(
        self,
        point: Union[
            gpxpy.gpx.GPXWaypoint, gpxpy.gpx.GPXRoutePoint, gpxpy.gpx.GPXTrackPoint
        ],
        use_departure: Optional[bool] = False,
    ) -> Optional[datetime]:
        """returns datetime object for route point with departure times or None"""
        if use_departure and self.depart_at:
            return self.depart_at
        for extension in point.extensions:
            for departure in extension.findall("trp:DepartureTime", XML_NAMESPACE):
                return datetime.fromisoformat(departure.text.replace("Z", "+00:00"))
        return None

    def sun_rise_set(
        self,
        start: Union[gpxpy.gpx.GPXRoutePoint, gpxpy.gpx.GPXTrackPoint],
        end: Union[gpxpy.gpx.GPXRoutePoint, gpxpy.gpx.GPXTrackPoint],
        delay: Optional[timedelta] = None,
    ) -> str:
        """return sunrise/sunset and start & end info based upon the route start and end point"""
        if not start.time or not end.time:
            return ""
        sun_start = astral.sun.sun(
            astral.LocationInfo(
                "Start Point", "", "", start.latitude, start.longitude
            ).observer,
            date=start.time,
        )
        sun_end = astral.sun.sun(
            astral.LocationInfo(
                "End Point", "", "", end.latitude, end.longitude
            ).observer,
            date=start.time,
        )
        times = {
            "Sunrise": sun_start["sunrise"],
            "Sunset": sun_end["sunset"],
            "Starts": start.time,
            "Ends": end.time + (delay or timedelta()),
        }
        first = True
        retval = f"{start.time.astimezone():%x}: "
        for name, time in sorted(times.items(), key=lambda kv: kv[1]):
            if first is not True:
                retval += ", "
            first = False
            retval += f"{name}: {time.astimezone():%H:%M}"
        return retval

    @staticmethod
    def is_gas(point: Union[gpxpy.gpx.GPXWaypoint, gpxpy.gpx.GPXRoutePoint]) -> str:
        if (
            point.symbol
            and "Gas Station" in point.symbol
            or re.search(r"\bGas\b|\bFuel\b", point.name or "", re.I)
        ):
            return "G"
        return ""

    @staticmethod
    def is_meal(point: Union[gpxpy.gpx.GPXWaypoint, gpxpy.gpx.GPXRoutePoint]) -> str:
        if (
            point.symbol
            and "Restaurant" in point.symbol
            or re.search(
                r"\bRestaurant\b|\bLunch\b|\bBreakfast\b|\b\Dinner\b",
                point.name or "",
                re.I,
            )
        ):
            return "L"
        return ""

    @staticmethod
    def is_scenic_area(
        point: Union[gpxpy.gpx.GPXWaypoint, gpxpy.gpx.GPXRoutePoint]
    ) -> str:
        if (
            point.symbol
            and "Scenic Area" in point.symbol
            or re.search(r"\bScenic Area\b|\bPhoto\b", point.name or "", re.I)
        ):
            return "P"
        return ""

    @staticmethod
    def shaping_point(
        point: Union[gpxpy.gpx.GPXWaypoint, gpxpy.gpx.GPXRoutePoint]
    ) -> bool:
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


def create_markdown(args) -> None:
    for handle in args.input:
        with handle as stream:
            try:
                table = GPXTableCalculator(
                    gpxpy.parse(stream),
                    imperial=not args.metric,
                    speed=args.speed,
                    depart_at=args.departure,
                )
                table.display_coordinates = args.coordinates
                table.print_header()
                table.print_waypoints()
                table.print_routes()
            except gpxpy.gpx.GPXException as err:
                raise SystemExit(f"{handle.name}: {err}") from err


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", nargs="+", type=argparse.FileType("r"), help="input file(s)"
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
    parser.add_argument(
        "--coordinates",
        action="store_true",
        help="Display latitude and longitude of waypoints",
    )

    try:
        args = parser.parse_args()
    except ValueError as err:
        raise SystemExit(err) from err

    if args.html:
        with io.StringIO() as buffer:
            real_stdout = sys.stdout
            sys.stdout = buffer
            create_markdown(args)
            sys.stdout = real_stdout
            buffer.flush()
            print(markdown2.markdown(buffer.getvalue(), extras=["tables"]))
    else:
        create_markdown(args)


if __name__ == "__main__":
    main()
