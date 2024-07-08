import pytest
from datetime import datetime, timezone
from io import StringIO
from typing import Tuple

from gpxpy.gpx import (
    GPX,
    GPXRoute,
    GPXRoutePoint,
    GPXTrackSegment,
    GPXTrackPoint,
    GPXTrack,
)
from gpxpy.geo import Location
from gpxtable.gpxtable import GPXTableCalculator, GPXTrackExt


@pytest.fixture
def gpx_data() -> Tuple[GPX, StringIO]:
    gpx = GPX()
    gpx.author_name = "John Doe"
    gpx.author_email = "unittest@example.com"
    gpx.creator = "Unit Test Creator"
    gpx.description = "Unit Test Description"
    gpx.name = "Unit Test GPX Name"

    track = GPXTrack(
        name="Unit Test Track Name", description="Unit Test Track Description"
    )
    segment = GPXTrackSegment()
    segment.points.extend(
        [
            GPXTrackPoint(
                48.2081743,
                16.3738189,
                elevation=160,
                time=datetime(2023, 7, 3, 10, 0, 0, tzinfo=timezone.utc),
            ),
            GPXTrackPoint(
                48.2181743,
                16.4738189,
                elevation=160,
                time=datetime(2023, 7, 3, 11, 0, 0, tzinfo=timezone.utc),
            ),
        ]
    )
    track.segments.append(segment)
    gpx.tracks.append(track)

    route = GPXRoute(
        name="Unit Test Route Name", description="Unit Test Route Description"
    )
    route.points.extend(
        [
            GPXRoutePoint(
                48.2081743,
                16.3738189,
                time=datetime(2023, 7, 3, 10, 0, 0, tzinfo=timezone.utc),
                name="Route Start",
                symbol="Circle, Green",
            ),
            GPXRoutePoint(
                48.2181743,
                16.4738189,
                time=datetime(2023, 7, 3, 11, 0, 0, tzinfo=timezone.utc),
                name="Route End",
                symbol="Circle, Blue",
            ),
        ]
    )
    gpx.routes.append(route)

    output = StringIO()

    return gpx, output


def test_print_header(gpx_data: Tuple[GPX, StringIO]) -> None:
    gpx, output = gpx_data
    calculator = GPXTableCalculator(gpx, output)
    calculator.print_header()
    assert (
        output.getvalue()
        == """## Unit Test GPX Name
* Unit Test Creator
* Total moving time: 01:00:00
* Total distance: 5 mi
* Default speed: 48.28 mph
"""
    )


def test_print_waypoints(gpx_data: Tuple[GPX, StringIO]) -> None:
    gpx, output = gpx_data
    calculator = GPXTableCalculator(gpx, output)
    calculator.print_waypoints()
    assert "## Track:" in output.getvalue()


def test_print_routes(gpx_data: Tuple[GPX, StringIO]) -> None:
    gpx, output = gpx_data
    calculator = GPXTableCalculator(gpx, output)
    calculator.print_routes()
    assert "## Route:" in output.getvalue()
    assert (
        """
## Route: Unit Test Route Name
* Unit Test Route Description

| Name                           |   Dist. | GL |  ETA  | Notes
| :----------------------------- | ------: | -- | ----: | :----
| Route Start                    |       0 |    |       | Circle, Green
| Route End                      |     0/0 |    |       | Circle, Blue
"""
        in output.getvalue()
    )


def test_get_points_data(gpx_data: Tuple[GPX, StringIO]) -> None:
    gpx, _ = gpx_data
    track_ext = GPXTrackExt(gpx.tracks[0])
    points_data = track_ext.get_points_data()
    assert len(points_data) == 2


def test_get_nearest_locations(gpx_data: Tuple[GPX, StringIO]) -> None:
    gpx, _ = gpx_data
    location = Location(48.2081744, 16.3738188)
    track_ext = GPXTrackExt(gpx.tracks[0])
    nearest_locations = track_ext.get_nearest_locations(location)
    assert len(nearest_locations) == 1


if __name__ == "__main__":
    pytest.main()
