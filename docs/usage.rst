Usage
=====

.. _installation:

Installation
------------

To use GPXtr, first install it using pip. We require a recent python (tested with python 3.9+).

Consider using `Python virtual environments`_ to avoid dependency conflicts.

This code is under rapid development so please install the latest version
in the GitHub repository.

.. code-block:: console

   $ python3 -m pip install https://github.com/pleasantone/gpxtr/

Using gpxtr
-----------

Once installed, you should be able to invoke it as *gpxtr*.

.. code-block:: console

   $ gpxtr --help
   usage: gpxtr [-h] [--output OUTPUT] [--sort SORT] [--departure DEPARTURE] [--speed SPEED] [--html] [--metric] input [input ...]

   positional arguments:
   input                 input file(s)

   optional arguments:
   -h, --help            show this help message and exit
   --output OUTPUT       output file
   --sort SORT           sort algorithm (for waypoints only)
   --departure DEPARTURE
                         set departure time for first point (local timezone)
   --speed SPEED         set average travel speed
   --html                output in HTML, not markdown
   --metric              Use metric units (default imperial)


.. _Python virtual environments: https://docs.python.org/3/library/venv.html
