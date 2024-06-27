gpxtable
========

GPXtable -- your trip planning helper

GPXtable was created based upon the need to assist motorcycle riders and trip planners
to determine the most important things:

* When is lunch?
* Do I have enough gas to get to the next fuel stop?

While the impetus was motorcycle travel, it works for any sort of trip planning.
Unlike most software, it can read both routes as well as tracks. It will do its
best to match waypoints to locations on a track to calculate time and distances.

In the following example, a GPX route was produced in Garmin's Basecamp application.

.. code-block:: console

   $ gpxtable testdata/basecamp-route.gpx
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

We also include sunrise and sunset so you know when you're going to get there.

If you're using tracks and waypoints, since they don't typically have valid timestamps, you'll
need to specify your departure time.

This software has been heavily tested with output from Basecamp, Scenic, InRoute, RideWithGPS,
as well as several other routing applications.

Full documentation
==================

Main documentation available at <http://gpxtable.readthedocs.io/>.

.. image:: https://readthedocs.org/projects/gpxtable/badge/?version=latest
   :target: https://gpxtable.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status
