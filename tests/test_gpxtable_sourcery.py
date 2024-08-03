import pytest
from datetime import datetime, timedelta, timezone

from io import StringIO
from gpxpy.gpx import (
    GPX,
    GPXTrack,
    GPXTrackSegment,
    GPXTrackPoint,
    GPXRoute,
    GPXRoutePoint,
    GPXWaypoint,
)
from gpxtable import GPXTableCalculator


@pytest.fixture
def gpx_data():
    gpx = GPX()
    track = GPXTrack()
    segment = GPXTrackSegment()
    segment.points.append(
        GPXTrackPoint(
            latitude=52.0,
            longitude=0.0,
            time=datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
        )
    )
    segment.points.append(
        GPXTrackPoint(
            latitude=52.1,
            longitude=0.1,
            time=datetime(2023, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        )
    )
    track.segments.append(segment)
    gpx.tracks.append(track)
    gpx.waypoints.append(
        GPXWaypoint(latitude=52.0, longitude=0.0, name="Start", symbol="Waypoint")
    )
    gpx.waypoints.append(
        GPXWaypoint(latitude=52.0, longitude=0.1, name="End", symbol="Waypoint")
    )
    return gpx


@pytest.fixture
def output_stream():
    return StringIO()


@pytest.mark.parametrize(
    (
        "imperial",
        "speed",
        "depart_at",
        "ignore_times",
        "display_coordinates",
        "tz",
        "expected_output",
    ),
    [
        (
            True,
            30.0,
            datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
            False,
            False,
            None,
            "\n## Track: None\n\n| Name                           |   Dist. | GL |  ETA  | Notes\n| :----------------------------- | ------: | -- | ----: | :----\n",
        ),
        (
            False,
            50.0,
            datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
            True,
            True,
            None,
            "\n## Track: None\n\n|        Lat,Lon       | Name                           |   Dist. | GL |  ETA  | Notes\n| :------------------: | :----------------------------- | ------: | -- | ----: | :----\n",
        ),
    ],
    ids=["imperial_true", "imperial_false"],
)
def test_print_waypoints(
    gpx_data,
    output_stream,
    imperial,
    speed,
    depart_at,
    ignore_times,
    display_coordinates,
    tz,
    expected_output,
):
    # Arrange
    calculator = GPXTableCalculator(
        gpx=gpx_data,
        output=output_stream,
        imperial=imperial,
        speed=speed,
        depart_at=depart_at,
        ignore_times=ignore_times,
        display_coordinates=display_coordinates,
        tz=tz,
    )

    # Act
    calculator.print_waypoints()

    # Assert
    output_stream.seek(0)
    assert output_stream.read().startswith(expected_output)


@pytest.mark.parametrize(
    (
        "imperial",
        "speed",
        "depart_at",
        "ignore_times",
        "display_coordinates",
        "tz",
        "expected_output",
    ),
    [
        (
            True,
            30.0,
            datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
            False,
            False,
            timezone.utc,
            "* Departure at Sun Jan  1 08:00:00 2023 UTC\n* Total moving time: 01:00:00\n* Total distance: 8 mi\n* Default speed: 30.00 mph\n",
        ),
        (
            False,
            50.0,
            datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
            True,
            True,
            timezone.utc,
            "* Departure at Sun Jan  1 08:00:00 2023 UTC\n* Total moving time: 01:00:00\n* Total distance: 13 km\n* Default speed: 50.00 km/h\n",
        ),
    ],
    ids=["imperial_true", "imperial_false"],
)
def test_print_header(
    gpx_data,
    output_stream,
    imperial,
    speed,
    depart_at,
    ignore_times,
    display_coordinates,
    tz,
    expected_output,
):
    # Arrange
    calculator = GPXTableCalculator(
        gpx=gpx_data,
        output=output_stream,
        imperial=imperial,
        speed=speed,
        depart_at=depart_at,
        ignore_times=ignore_times,
        display_coordinates=display_coordinates,
        tz=tz,
    )

    # Act
    calculator.print_header()

    # Assert
    output_stream.seek(0)
    assert output_stream.read() == expected_output


@pytest.mark.parametrize(
    (
        "imperial",
        "speed",
        "depart_at",
        "ignore_times",
        "display_coordinates",
        "tz",
        "expected_output",
    ),
    [
        (
            True,
            30.0,
            datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
            False,
            False,
            timezone.utc,
            "\n## Route: None\n\n| Name                           |   Dist. | GL |  ETA  | Notes\n| :----------------------------- | ------: | -- | ----: | :----\n",
        ),
        (
            False,
            50.0,
            datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
            True,
            True,
            timezone.utc,
            "\n## Route: None\n\n|        Lat,Lon       | Name                           |   Dist. | GL |  ETA  | Notes\n| :------------------: | :----------------------------- | ------: | -- | ----: | :----\n",
        ),
    ],
    ids=["imperial_true", "imperial_false"],
)
def test_print_routes(
    gpx_data,
    output_stream,
    imperial,
    speed,
    depart_at,
    ignore_times,
    display_coordinates,
    tz,
    expected_output,
):
    # Arrange
    route = GPXRoute()
    route.points.append(
        GPXRoutePoint(
            latitude=52.0,
            longitude=0.0,
            time=datetime(2023, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
        )
    )
    route.points.append(
        GPXRoutePoint(
            latitude=52.1,
            longitude=0.1,
            time=datetime(2023, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        )
    )
    gpx_data.routes.append(route)
    calculator = GPXTableCalculator(
        gpx=gpx_data,
        output=output_stream,
        imperial=imperial,
        speed=speed,
        depart_at=depart_at,
        ignore_times=ignore_times,
        display_coordinates=display_coordinates,
        tz=tz,
    )

    # Act
    calculator.print_routes()

    # Assert
    output_stream.seek(0)
    assert output_stream.read().startswith(expected_output)


@pytest.mark.parametrize(
    ("time_s", "expected_output"),
    [
        (0, "n/a"),
        (3661, "01:01:01"),
    ],
    ids=["zero_time", "non_zero_time"],
)
def test_format_time(time_s, expected_output):
    # Act
    result = GPXTableCalculator._format_time(time_s)

    # Assert
    assert result == expected_output


@pytest.mark.parametrize(
    ("length", "imperial", "units", "expected_output"),
    [
        (1000, True, True, "1 mi"),
        (1000, False, True, "1 km"),
        (1000, True, False, "1"),
        (1000, False, False, "1"),
    ],
    ids=[
        "imperial_with_units",
        "metric_with_units",
        "imperial_without_units",
        "metric_without_units",
    ],
)
def test_format_long_length(length, imperial, units, expected_output):
    # Arrange
    calculator = GPXTableCalculator(gpx=GPX(), imperial=imperial)

    # Act
    result = calculator._format_long_length(length, units)

    # Assert
    assert result == expected_output


@pytest.mark.parametrize(
    ("length", "imperial", "units", "expected_output"),
    [
        (1, True, True, "3.28 ft"),
        (1, False, True, "1.00 m"),
        (1, True, False, "3.28"),
        (1, False, False, "1.00"),
    ],
    ids=[
        "imperial_with_units",
        "metric_with_units",
        "imperial_without_units",
        "metric_without_units",
    ],
)
def test_format_short_length(length, imperial, units, expected_output):
    # Arrange
    calculator = GPXTableCalculator(gpx=GPX(), imperial=imperial)

    # Act
    result = calculator._format_short_length(length, units)

    # Assert
    assert result == expected_output


@pytest.mark.parametrize(
    ("speed", "imperial", "units", "expected_output"),
    [
        (50, True, True, "31.07 mph"),
        (50, False, True, "50.00 km/h"),
        (50, True, False, "31.07"),
        (50, False, False, "50.00"),
    ],
    ids=[
        "imperial_with_units",
        "metric_with_units",
        "imperial_without_units",
        "metric_without_units",
    ],
)
def test_format_speed(speed, imperial, units, expected_output):
    # Arrange
    calculator = GPXTableCalculator(gpx=GPX(), imperial=imperial)

    # Act
    result = calculator._format_speed(speed, units)

    # Assert
    assert result == expected_output


@pytest.mark.parametrize(
    ("dist", "speed", "expected_output"),
    [
        (1000, 50, timedelta(minutes=1.2)),
        (2000, 100, timedelta(minutes=1.2)),
    ],
    ids=["dist_1000_speed_50", "dist_2000_speed_100"],
)
def test_travel_time(dist, speed, expected_output):
    # Arrange
    calculator = GPXTableCalculator(gpx=GPX(), speed=speed, imperial=False)

    # Act
    result = calculator._travel_time(dist)

    # Assert
    assert result == expected_output
