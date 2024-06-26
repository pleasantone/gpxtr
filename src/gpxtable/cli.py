# pylint: disable=line-too-long, missing-function-docstring
"""
gpxtable - Create a markdown template from a Garmin GPX file for route information
"""

import argparse
import io
from datetime import datetime

import dateutil.parser
import dateutil.tz
import gpxpy.gpx
import gpxpy.geo
import gpxpy.utils
import markdown2

from gpxtable import GPXTableCalculator


def create_markdown(args, output=None) -> None:
    for handle in args.input:
        with handle as stream:
            try:
                GPXTableCalculator(
                    gpxpy.parse(stream),
                    output=output,
                    imperial=not args.metric,
                    speed=args.speed,
                    depart_at=args.departure,
                    display_coordinates=args.coordinates,
                    ignore_times=args.ignore_times,
                ).print_all()
            except gpxpy.gpx.GPXException as err:
                raise SystemExit(f"{handle.name}: {err}") from err


class _DateParser(argparse.Action):
    """
    Argparse extension to support natural date parsing.

    Date string must be sent in complete so needs quoting on command line.
    :meta private:
    """

    def __call__(self, parser, namespace, values, option_strings=None):
        setattr(
            namespace,
            self.dest,
            dateutil.parser.parse(
                values,
                default=datetime.now(dateutil.tz.tzlocal()).replace(
                    second=0, microsecond=0
                ),
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", nargs="+", type=argparse.FileType("r"), help="input file(s)"
    )
    parser.add_argument(
        "--departure",
        default=None,
        action=_DateParser,
        help="set departure time for first point (local timezone)",
    )
    parser.add_argument(
        "--ignore-times", action="store_true", help="Ignore track times"
    )
    parser.add_argument(
        "--speed", default=0.0, type=float, help="set average travel speed"
    )
    parser.add_argument(
        "--html", action="store_true", help="output in HTML, not markdown"
    )
    parser.add_argument(
        "--metric", action="store_true", help="Use metric units (default imperial)"
    )
    parser.add_argument(
        "--coordinates",
        action="store_true",
        help="Display latitude and longitude of waypoints",
    )

    try:
        args = parser.parse_args()
    except ValueError as err:
        raise SystemExit(err) from err

    if args.html:
        with io.StringIO() as buffer:
            create_markdown(args, output=buffer)
            buffer.flush()
            print(markdown2.markdown(buffer.getvalue(), extras=["tables"]))
    else:
        create_markdown(args)


if __name__ == "__main__":
    main()
