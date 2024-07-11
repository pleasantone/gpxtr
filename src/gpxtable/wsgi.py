# pylint: disable=line-too-long, missing-function-docstring
"""
gpxtable - Create a markdown template from a Garmin GPX file for route information
"""

import io
import html
import requests
import secrets
from datetime import datetime
from flask import Flask, request, flash, redirect, render_template, abort, url_for

import dateutil.parser
import dateutil.tz
import gpxpy.gpx
import gpxpy.geo
import gpxpy.utils
import markdown2
import validators

from gpxtable import GPXTableCalculator

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000  # 16mb
app.config["SECRET_KEY"] = secrets.token_urlsafe(16)


def create_table(stream, tz=None) -> str:
    try:

        depart_at = None
        departure = request.form.get("departure")
        if not tz:
            tz = dateutil.tz.tzlocal()
        if departure:
            depart_at = dateutil.parser.parse(
                departure,
                default=datetime.now(tz).replace(minute=0, second=0, microsecond=0),
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
                tz=tz,
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
        if "url" not in request.form and "file" not in request.files:
            flash("Missing URL for GPX file or uploaded file.")
            return redirect(url_for("upload_file"))

        if "url" in request.form and (url := request.form.get("url")):
            if not validators.url(url):
                flash("Invalid URL")
                return redirect(url_for("upload_file"))
            response = requests.get(url)
            if response.status_code == 200:
                file = io.BytesIO(response.content)
            else:
                flash(
                    "Error fetching the GPX file from the provided URL: {response.reason}"
                )
                return redirect(url_for("upload_file"))
        elif "file" in request.files:
            file = request.files["file"]
            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if not file.filename:
                flash("No file selected")
                return redirect(url_for("upload_file"))

        tz = None
        timezone = request.form.get("tz")
        if timezone:
            tz = dateutil.tz.gettz(timezone)
            if not tz:
                flash("Invalid timezone")
                return redirect(url_for("upload_file"))
        return create_table(file, tz=tz)
    return render_template("upload.html")


@app.route("/about")
def about():
    return render_template("about.html")
