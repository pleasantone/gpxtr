# pylint: disable=line-too-long, missing-function-docstring
"""
gpxtable - Create a markdown template from a Garmin GPX file for route information
"""

import io
import html
from datetime import datetime
from flask import Flask, request, flash, redirect, render_template, abort

import dateutil.parser
import dateutil.tz
import gpxpy.gpx
import gpxpy.geo
import gpxpy.utils
import markdown2


from . import GPXTableCalculator

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000  # 16mb


def create_table(stream) -> str:
    try:

        depart_at = None
        departure = request.form.get("departure")
        if departure:
            depart_at = dateutil.parser.parse(
                departure,
                default=datetime.now(dateutil.tz.tzlocal()).replace(
                    second=0, microsecond=0
                ),
            )

        with io.StringIO() as buffer:
            GPXTableCalculator(
                gpxpy.parse(stream),
                output=buffer,
                depart_at=depart_at,
                ignore_times=request.form.get("ignore_times") == "on",
                display_coordinates=request.form.get("coordinates") == "on",
                imperial=request.form.get("metric") != "on",
                speed=float(request.form.get("speed") or 0.0),
            ).print_all()

            buffer.flush()
            output = buffer.getvalue()
            if request.form.get("output") == "markdown":
                return "<pre>" + output + "</pre>"
            output = markdown2.markdown(output, extras=["tables"])
            if request.form.get("output") == "htmlcode":
                return "<pre>" + html.escape(output) + "</pre>"
            return output
    except gpxpy.gpx.GPXException as err:
        abort(401, f"{stream.filename}: {err}")


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["file"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        return create_table(file)
    return render_template("upload.html")
