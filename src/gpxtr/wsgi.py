# pylint: disable=line-too-long, missing-function-docstring
"""
GPXtr - Create a markdown template from a Garmin GPX file for route information
"""

import io
import os
import sys
import html
from datetime import datetime
from flask import (
    Flask,
    request,
    flash,
    redirect,
    render_template,
    send_from_directory,
    abort,
)
from werkzeug.utils import secure_filename

import dateutil.parser
import dateutil.tz
import gpxpy.gpx
import gpxpy.geo
import gpxpy.utils
import markdown2


from .gpxtr import GPXTableCalculator, DEFAULT_TRAVEL_SPEED

UPLOAD_FOLDER = "/tmp"
ALLOWED_EXTENSIONS = {"gpx"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000  # 16mb


def create_table(name) -> str:
    try:
        with open(name, "rt", encoding="utf-8") as stream:
            with io.StringIO() as buffer:
                real_stdout = sys.stdout
                sys.stdout = buffer

                table = GPXTableCalculator(gpxpy.parse(stream))

                depart_at = request.form.get("departure")
                if depart_at:
                    table.depart_at = dateutil.parser.parse(
                        depart_at, default=datetime.now(dateutil.tz.tzlocal())
                    )
                table.ignore_times = request.form.get("ignore_times") == "on"
                table.display_coordinates = request.form.get("coordinates") == "on"
                table.imperial = request.form.get("metric") != "on"
                table.speed = int(
                    request.form.get("speed", DEFAULT_TRAVEL_SPEED)
                    or DEFAULT_TRAVEL_SPEED
                )

                table.print_header()
                table.print_waypoints()
                table.print_routes()

                sys.stdout = real_stdout
                buffer.flush()
                output = buffer.getvalue()
                if request.form.get("output") == "markdown":
                    return "<pre>" + output + "</pre>"
                output = markdown2.markdown(output, extras=["tables"])
                if request.form.get("output") == "htmlcode":
                    return "<pre>" + html.escape(output) + "</pre>"
                return output
    except gpxpy.gpx.GPXException as err:
        abort(401, f"{name}: {err}")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            savefile = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(savefile)
            return create_table(savefile)
    return render_template("upload.html", speed=DEFAULT_TRAVEL_SPEED)


@app.route("/uploads/<name>")
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)
