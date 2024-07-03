import unittest
import gpxpy
import gpxpy.gpx
from datetime import datetime, timezone
from io import StringIO
from gpxtable.gpxtable import GPXTableCalculator, GPXTrackExt


class TestGPXTableCalculator(unittest.TestCase):
    def setUp(self):
        # Setup a sample GPX object
        gpx = gpxpy.gpx.GPX()
        gpx.author_name = "John Doe"
        gpx.author_email = "nobody@example.com"
        gpx.creator = "Python Unit Test"
        gpx.description = "Python Unit Test GPX Element"
        gpx.name = "Unit Test GPX Name"
        track = gpxpy.gpx.GPXTrack()
        track.name = "Unit Test Track"
        gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)
        point = gpxpy.gpx.GPXTrackPoint(
            48.2081743,
            16.3738189,
            elevation=160,
            time=datetime(2023, 7, 3, 10, 0, 0, tzinfo=timezone.utc),
        )
        segment.points.append(point)
        point = gpxpy.gpx.GPXTrackPoint(
            48.2181743,
            16.4738189,
            elevation=160,
            time=datetime(2023, 7, 3, 11, 0, 0, tzinfo=timezone.utc),
        )
        segment.points.append(point)

        route = gpxpy.gpx.GPXRoute()
        gpx.routes.append(route)
        route.name = "Python Unit Test Route Name"
        route.description = "Python Unit Test Route Description"
        route_point = gpxpy.gpx.GPXRoutePoint(
            48.2081743,
            16.3738189,
            time=datetime(2023, 7, 3, 10, 0, 0, tzinfo=timezone.utc),
            name="Route Start",
            symbol="Circle, Green",
        )
        route.points.append(route_point)
        route_point = gpxpy.gpx.GPXRoutePoint(
            48.2181743,
            16.4738189,
            time=datetime(2023, 7, 3, 11, 0, 0, tzinfo=timezone.utc),
            name="Route End",
            symbol="Circle, Blue",
        )
        route.points.append(route_point)
        self.gpx = gpx
        self.output = StringIO()
        self.depart_at = datetime(2023, 7, 3, 10, 0, 0, tzinfo=timezone.utc)

    def test_print_header(self):
        calculator = GPXTableCalculator(self.gpx, self.output)
        calculator.print_header()
        self.assertIn("##", self.output.getvalue())

    def test_print_waypoints(self):
        calculator = GPXTableCalculator(self.gpx, self.output)
        calculator.print_waypoints()
        self.assertIn("## Track:", self.output.getvalue())

    def test_print_routes(self):
        calculator = GPXTableCalculator(self.gpx, self.output)
        calculator.print_routes()
        self.assertIn("## Route:", self.output.getvalue())

    def test_get_points_data(self):
        track_ext = GPXTrackExt(self.gpx.tracks[0])
        points_data = track_ext.get_points_data()
        self.assertEqual(len(points_data), 2)

    def test_get_nearest_locations(self):
        location = gpxpy.geo.Location(48.2081744, 16.3738188)
        track_ext = GPXTrackExt(self.gpx.tracks[0])
        nearest_locations = track_ext.get_nearest_locations(location)
        self.assertEqual(len(nearest_locations), 1)


if __name__ == "__main__":
    unittest.main()
