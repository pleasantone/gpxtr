Usage
=====

Once installed, invoke the command line script as `gpxtable`.

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

The output is a human-readable markdown-format table which may be included in
published information about the trip. Additionally, `gpxtable` can produce HTML
format output using the `--html` option.

Background and limitations
--------------------------
GPX files contain three types of data, waypoints, tracks, and routes.

*Tracks* consist of one or several ordered lists of latitude/longitude track
points. These points on a track are typically close together but do not contain
any information suitable for routing or contain any information about points of
interest along a "track." Tracks were originally designed as simple
"breadcrumbs" of where a GPS had gone, or may be used to project where one will
be going. Tracks typically have no routing information and provide no guidance.

*Waypoints* are independent points of interest in a GPX file. They are not
necessarily associated with tracks or routes at all, they are just pins in the
map and have no ordering. They are not associated with any route or track.

*Routes* are an ordered list of *route points* describing a straight-line path
between each route point. Route points may be *via/shaping points* which are
typically used just for route calculations, or *stops* which are announced by
the navigator. Routes have a major problem, they provide just enough information
for the GPS to calculate a route, but each GPS vendor, and in fact, each map
version from the same vendor, may alter the routing. There is no uniformity
and no guarantee that the route will be identical to what the author intended.

For that reason, most authors prefer to distribute GPX tracks over routes.

.. note::
   Garmin produced extensions to GPX format to include a track segment linking each
   route point, and the ability to specify layover times at route points, which
   truly is the best of all worlds. However, even a modern Garmin GPS may
   recalculate a route from scratch if one goes off-route.


Example: Building a table from a Route (as produced by Basecamp)
----------------------------------------------------------------

In this example, we have used sample data to produce the most accurate output as
intended by the route author. The author specified delays and layovers in the
route configuration itself in Basecamp. These may be overridden with the flag
`--ignore-times` if desired, in which case `gpxtable` will calculate new times
based upon the `--departure` and `--speed` options.

.. literalinclude:: ../samples/basecamp-route.md
   :caption: gpxtable samples/basecamp-route.gpx
   :language: text

Building a table from a track and waypoints
-------------------------------------------

In this example, we have only track and waypoint information.

`gpxtable` will match waypoints to the provided GPX tracks on a best effort
basis.  (Unlike GPX routes, tracks don't embed waypoints).

A `--departure` command line option should be specified to set the departure
time of the tracks. If there are multiple tracks in the GPX file, the program
will assume a track per day (use track segments to break up tracks).

Layover delays at waypoints may be automatically added based upon the waypoint
symbol type or by including keywords in the waypoint name.

        Restaurant: 1 hour        (Restaurant | Lunch | Breakfast | Dinner| (L))
        Gas Station: 15 minutes   (Gas | Fuel | (G))
        Restroom: 15 minutes      (Restroom | Break | (R))
        Photo: 5 minutes          (Scenic Area | Photos? | (P))
        Scenic Area: 5 minutes

.. literalinclude:: ../samples/basecamp-route.md
   :caption: gpxtable --departure "07/30/2022 09:15:00" samples/basecamp-route.gpx
   :language: text

Limitations:

   - A waypoint will be matched with the nearest point on it track, if a track
     doubles-back on itself, it's difficult to tell if a waypoint is on the
     outbound or inbound leg.

   - A pseudo-waypoint will be added indicating the last point in the track. If
     this is redundant with the final waypoint, it will not be added.
