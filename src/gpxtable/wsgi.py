# pylint: disable=line-too-long, missing-function-docstring
"""
gpxtable - Create a markdown template from a Garmin GPX file for route information
"""

import io
import html
import secrets
from datetime import datetime
from flask import (
    Flask,
    request,
    flash,
    redirect,
    render_template,
    url_for,
)

import dateutil.parser
import dateutil.tz
import gpxpy.gpx
import gpxpy.geo
import gpxpy.utils
import markdown2
import requests
import validators

from gpxtable import GPXTableCalculator


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000  # 16mb
app.config["SECRET_KEY"] = secrets.token_urlsafe(16)


class InvalidSubmission(Exception):
    """Exception for invalid form submission"""


@app.errorhandler(InvalidSubmission)
def invalid_submission(err):
    flash(str(err))
    app.logger.info(err)
    return redirect(url_for("upload_file"))


def create_table(stream, tz=None):  # sourcery skip: extract-method
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
        try:
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
        except gpxpy.gpx.GPXXMLSyntaxException as err:
            raise InvalidSubmission(f"Unable to parse GPX information: {err}") from err

        buffer.flush()
        output = buffer.getvalue()
        if request.form.get("output") == "markdown":
            return output
        output = str(markdown2.markdown(output, extras=["tables"]))
        if request.form.get("output") == "htmlcode":
            return html.escape(output)
        return output


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method != "POST":
        return render_template("upload.html")
    if url := request.form.get("url"):
        if not validators.url(url):
            raise InvalidSubmission("Invalid URL")
        try:
            response = requests.get(url, timeout=30)
        except requests.ConnectionError as err:
            raise InvalidSubmission(f"Unable to retrieve URL: {err}") from err
        if response.status_code == 200:
            file = io.BytesIO(response.content)
        else:
            raise InvalidSubmission(
                f"Error fetching the GPX file from the provided URL: {response.reason}"
            )
    elif file := request.files.get("file"):
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if not file.filename:
            raise InvalidSubmission("No file selected")
    else:
        raise InvalidSubmission("Missing URL for GPX file or uploaded file.")

    tz = None
    if timezone := request.form.get("tz"):
        tz = dateutil.tz.gettz(timezone)
        if not tz:
            raise InvalidSubmission("Invalid timezone")

    if isinstance(result := create_table(file, tz=tz), str):
        return render_template(
            "results.html", output=result, format=request.form.get("output")
        )
    return result


@app.route("/about")
def about():
    return render_template("about.html")
