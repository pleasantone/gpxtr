gpxtable - create tables from GPX information to aid in travel planning
=======================================================================

GPXtable was created based upon the need to assist motorcycle riders and trip planners
to determine the most important things:

* When is lunch?
* Do I have enough gas to get to the next fuel stop?

While the impetus was motorcycle travel, it works for any sort of trip planning.
Unlike most software, it can read both routes as well as tracks. It will do its
best to match waypoints to locations on a track to calculate time and distances.

Example:

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

Distance from start is included, as is distance between fuel stops if the fuel
stops are labeled properly. We can also specify layover times based upon the type
of stop.

`gpxtable` also includes sunrise and sunset so you if you are traveling in the dark.

This software has been heavily tested with output from Basecamp, Scenic, InRoute, RideWithGPS,
as well as several other routing applications.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
