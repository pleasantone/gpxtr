# gpxtr

GPX table translate - extract info from a GPX file to produce markdown data for ride descriptions

Notes:

- This uses GPX routes and waypoints, and does not rely on tracks.
- This produces output in Markdown
- If you set the symbol type for the type of waypoint (e.g. in Basecamp), it will include that in the Notes section and set gas markers as well.
- If you use departure times or layover times in Basecamp, it respects those as well.
- Computes sunrise & sunset based upon start point of route.

Use:

1. Install latest version of python on your system, the executable will be called
   "python" or "python3" -- I'll assume python3/pip3
2. There is a python library installation program, pip3 (or pip) that we use for
   installing the dependencies for this program.
3. `pip3 install gpxpy`
4. `pip3 install astral`
5. running `python3 gpxtr.py` -- should give you the output:

    ```bash
    $ python3 ./gpxtr.py
    usage: gpxtr.py [-h] input
    gpxtr.py: error: the following arguments are required: input
    ```

    If not, one of the dependencies is missing.

6. Test it against sample input file, should generate the following output...

    ```text
    $ python3 ./gpxtr.py fort-ross.gpx
    | Stop |      Lat,Lon       | Description                    | Miles | Gas  | Time  | Layover | Notes
    | ---: | :----------------: | :----------------------------- | ----: | :--: | ----: | ------: | :----
    |   01 |  38.0045,-122.5447 | Peet's Coffee Northgate Mall   |       |    G | 09:15 |         | Restaurant
    |   02 |  38.0621,-122.6987 | Nicasio Square                 |       |      |       |    +15m | Restroom
    |   03 |  38.5022,-122.9983 | Pat's International            |       |      |       |     +1h | Restaurant
    |   04 |  38.5018,-123.0001 | 76 Guerneville                  |       |    G |       |    +15m | Gas Station
    |   05 |  38.5352,-123.0871 | Willy's America                |       |      |       |     +5m | Truck
    |   06 |  38.3292,-123.0436 | 76 Bodega Bay                  |       |    G |       |    +15m | Gas Station
    |   07 |  38.0680,-122.8064 | Point Reyes Station            |       |      |       |     +5m | Restroom
    |   08 |  37.8979,-122.5150 | Starbucks Strawberry Village   |       |      |       |         | Restaurant

    Sunrise: 06:11, Sunset: 20:21
    ```

7. Cut and paste into your final file and manually edit in the miles and time from Basecamp's route report.

    ```text
    Sunrise: 06:11, Sunset: 20:21

    | Stop |      Lat,Lon       | Description                    | Miles | Gas  | Time  | Layover | Notes
    | ---: | :----------------: | :----------------------------- | ----: | :--: | ----: | ------: | :----
    |   01 |  38.0045,-122.5447 | Peet's Coffee Northgate Mall   |     0 |    G | 09:15 |         | KSU 9:15
    |   02 |  38.0621,-122.6987 | Nicasio Square                 |    12 |      | 09:44 |    +15m | Restroom
    |   03 |  38.5022,-122.9983 | Pat's International            |    65 |      | 11:27 |     +1h | Restaurant
    |   04 |  38.5018,-123.0001 | 76 Guerneville                 |    65 |    G | 12:27 |    +15m | Gas Station
    |   05 |  38.5352,-123.0871 | Willy's America                | 13/78 |      |  1:05 |     +5m | Photo Break
    |   06 |  38.3292,-123.0436 | 76 Bodega Bay                  |67/132 |    G |  3:06 |    +15m | Gas Station
    |   07 |  38.0680,-122.8064 | Point Reyes Station            |33/165 |      |  4:07 |     +5m | Restroom (optional)
    |   08 |  37.8979,-122.5150 | Starbucks Strawberry Village   |64/196 |      |  5:18 |         | Restaurant
    ```
