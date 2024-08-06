gpxtable - create tables from GPX information to aid in travel planning
=======================================================================

GPXtable was created based upon the need to assist motorcycle riders and trip planners
to determine the most important things:

* When is lunch?
* Do I have enough gas to get to the next fuel stop?

While the impetus was motorcycle travel, it works for any sort of trip planning.
Unlike most software, it can read both routes as well as tracks. It will do its
best to match waypoints to locations on a track to calculate time and distances.

GPXtable provides:

* A module that can be imported into your own software
* A command-line program wrapper
* An extensible Flask/WSGI wrapper

You can see an example of the WSGI wrapper at work at https://gpxtable.wn.r.appspot.com/

In the following example, a GPX route was produced in Garmin's Basecamp application,
the output is in Markdown_ which is human readable but also easily converted into
other formats like HTML.

.. _Markdown: https://www.markdownguide.org/

Example:

.. literalinclude:: ../samples/basecamp-route.md
   :language: text

Distance from start is included, as is distance between fuel stops if the fuel
stops are labeled properly. We can also specify layover times based upon the type
of stop.

We also includes sunrise and sunset so you can determine if you will be traveling in the dark.

This software has been heavily tested with output from Basecamp, Scenic, InRoute, RideWithGPS,
as well as several other routing applications.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   distribution
   installation
   usage
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
