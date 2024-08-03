import os
from flask.testing import FlaskClient
from flask import url_for
import pytest
import responses
from gpxtable.wsgi import create_app

TEST_FILE_URL = "http://mock.api/basecamp.gpx"
TEST_FILE = "samples/basecamp.gpx"
TEST_RESPONSE = b"Garmin Desktop App"
BAD_XML_FILE = "samples/bad-xml.gpx"


@pytest.fixture(scope="session")
def app():
    # add our fake responses
    with open(TEST_FILE, "rb") as f:
        responses.add(responses.GET, TEST_FILE_URL, status=200, body=f.read())
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


def test_index(client: FlaskClient) -> None:
    """Test the index page."""
    response = client.get(url_for("gpxtable.upload_file"))
    assert response.status_code == 200
    assert b"URL to GPX file" in response.data


def test_upload_file(client: FlaskClient) -> None:
    """Test file upload."""
    data = {"file": (open(TEST_FILE, "rb"), os.path.dirname(TEST_FILE))}
    response = client.post(
        url_for("gpxtable.upload_file"), data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 200
    assert TEST_RESPONSE in response.data


@responses.activate
def test_upload_url(client: FlaskClient) -> None:
    """Test URL submission."""

    response = client.post(
        url_for("gpxtable.upload_file"),
        data={"url": TEST_FILE_URL},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert TEST_RESPONSE in response.data


def test_bad_xml(client: FlaskClient) -> None:
    data = {"file": (open(BAD_XML_FILE, "rb"), os.path.dirname(BAD_XML_FILE))}
    response = client.post(
        url_for("gpxtable.upload_file"),
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.history  # it was redirected
    assert response.history[0].location == "/"
    assert b"Unable to parse" in response.data


if __name__ == "__main__":
    pytest.main()
