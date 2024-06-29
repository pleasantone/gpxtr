Usage
=====

.. _installation:

Installation
------------

To use gpxtable, first install it using pip. We require a recent python (tested with python 3.9+).

Consider using `Python virtual environments`_ to avoid dependency conflicts.

This code is under rapid development so please install the latest version
in the GitHub repository.

.. code-block:: console

   $ python3 -m pip install gpxtable

Using gpxtable
--------------

Once installed, you should be able to invoke it as *gpxtable*.

.. code-block:: console

   $ gpxtable --help
   usage: gpxtable [-h] [--departure DEPARTURE] [--ignore-times] [--speed SPEED]
             [--html] [--metric] [--coordinates]
             input [input ...]

   positional arguments:
      input                 input file(s)

   optional arguments:
      -h, --help            show this help message and exit
      --departure DEPARTURE
                            set departure time for first point (local timezone)
      --ignore-times        Ignore track times
      --speed SPEED         set average travel speed
      --html                output in HTML, not markdown
      --metric              Use metric units (default imperial)
      --coordinates         Display latitude and longitude of waypoints


.. _Python virtual environments: https://docs.python.org/3/library/venv.html

Background and limitations
--------------------------
GPX files contain three types of data, waypoints, tracks, and routes.

Tracks consist of one or several ordered lists of latitude/longitude points.
These points on a track are typically close together but do not contain any
information suitable for routing or contain any information about points of
interest along a "track." Tracks were originally designed as simple
"breadcrumbs" of where a GPS had gone, or may be used to project where it will
be going. Tracks typically have no routing information and provide no guidance.

Waypoints are independent points of interest in a GPX file. They are not
necessarily associated with tracks or routes at all, they are just pins in the
map and have no ordering. They are not associated with any route or track.

However, GPX routes are in some ways, the best of both tracks and waypoints.
They consist of an ordered list of waypoints. Historically, routes originally
just listed the points in order, and relied on the individual local GPX to
calculate the actual path between the points. However, Garmin produced
extensions to their routes to compute a track inside the route. This provides an
ordered list of points of interest (waypoints) as well as hidden waypoints that
shape the route itself as intended by the original author of the route.

Additionally route points may contain information like the type of point
(Restaurant, Restroom, etc.) and one may specify a departure time or layover
with each route point. This allows us to provide the most accurate information
for a route table.


ExampleL: Building a table from a Route (as produced by Basecamp)
-----------------------------------------------------------------

In this example, we have used test-data to produce the most accurate output as
intended by the route author. The author specified delays and layovers in the
route itself.

.. code-block:: console

   $ gpxtable samples/basecamp-route.gpx
   * Garmin Desktop App
   * Default speed: 30.00 mph

   ## Route: Fort Ross Run

   | Name                           |   Dist. | G |  ETA  | Notes
   | :----------------------------- | ------: | - | ----: | :----
   | Peet's Coffee Northgate Mall   |       0 |   | 09:15 | Restaurant
   | Nicasio Square                 |      12 |   | 09:39 | Restroom (+0:15)
   | Pat's International            |      65 | L | 11:41 | Restaurant (+1:00)
   | 76 Guerneville                 |   65/65 | G | 12:41 | Gas Station (+0:15)
   | Willy's America                |      79 |   | 13:23 | Scenic Area (+0:05)
   | 76 Bodega Bay                  |  67/132 | G | 15:14 | Gas Station (+0:15)
   | Point Reyes Station            |     165 |   | 16:36 | Restroom (+0:05)
   | Starbucks Strawberry Village   |  63/195 |   | 17:41 | Restaurant

   - 07/30/23: Sunrise: 06:11, Starts: 09:15, Ends: 17:41, Sunset: 20:20

Building a table from a track and waypoints
-------------------------------------------

In this example, we have a GPX file that only has track and waypoint
information.

In this case, we will match waypoints up with the provided tracks. Because of
the limitations of waypoints and tracks, a "departure time" for the track should
be provided and delays will be automatically chosen based upon the waypoint
type.

Since the waypoints in this test file were issued in alphabetical order, not
order of use, sort everything based upon the track_distance (distance from track
start) of a waypoint.

.. code-block:: console

   ❯ gpxtable --departure "07/30/2022 09:15:00" samples/basecamp-tracks.gpx
   * Garmin Desktop App
   * Departure at Sat Jul 30 09:15:00 2022
   * Total distance: 196 mi
   * Default speed: 30.00 mph

   ## Track: Fort Ross Run tk

   | Name                           |   Dist. | G |  ETA  | Notes
   | :----------------------------- | ------: | - | ----: | :----
   | Peet's Coffee Northgate Mall   |       0 |   | 09:15 | Restaurant
   | Nicasio Square                 |      12 |   | 09:39 | Restroom (+0:15)
   | Pat's International            |      65 | L | 11:40 | Restaurant (+1:00)
   | 76 Guerneville                 |   65/65 | G | 12:40 | Gas Station (+0:15)
   | Willy's America                |      79 |   | 13:22 | Scenic Area (+0:05)
   | 76 Bodega Bay                  |  67/132 | G | 15:14 | Gas Station (+0:15)
   | Point Reyes Station            |     165 |   | 16:35 | Restroom (+0:15)
   | Starbucks Strawberry Village   |  63/196 |   | 17:51 | Restaurant

   * 07/30/22: Sunrise: 06:11, Starts: 09:15, Ends: 17:51, Sunset: 20:20

Limitations:
   - a waypoint will be matched with the nearest point on it track, if a track
     doubles-back on itself, it's difficult to tell if a waypoint is on the outbound
     or inbound leg.
   - a pseudo-waypoint will be added indicating the last point in the track. If this is
     redundant with the final waypoint, one may be deleted.
