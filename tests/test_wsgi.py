import os
import io
from flask.testing import FlaskClient
from requests import HTTPError
import pytest
import responses
from gpxtable.wsgi import app

TEST_FILE_URL = "http://mock.api/basecamp.gpx"
TEST_FILE = "samples/basecamp.gpx"
TEST_RESPONSE = b"Garmin Desktop App"
BAD_XML_FILE = "samples/bad-xml.gpx"


@pytest.fixture
def client():
    # add our fake responses
    with open(TEST_FILE, "rb") as f:
        responses.add(responses.GET, TEST_FILE_URL, status=200, body=f.read())

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def test_index(client: FlaskClient):
    """Test the index page."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"URL to GPX file" in response.data


def test_upload_file(client: FlaskClient):
    """Test file upload."""
    data = {"file": (open(TEST_FILE, "rb"), os.path.dirname(TEST_FILE))}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert TEST_RESPONSE in response.data


@responses.activate
def test_upload_url(client: FlaskClient, monkeypatch: pytest.MonkeyPatch):
    """Test URL submission."""

    data = {"url": TEST_FILE_URL}
    response = client.post("/", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert TEST_RESPONSE in response.data


def test_bad_xml(client: FlaskClient):
    data = {"file": (open(BAD_XML_FILE, "rb"), os.path.dirname(BAD_XML_FILE))}
    response = client.post(
        "/", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert response.history  # it was redirected
    assert response.history[0].location == "/"
    assert b"Unable to parse" in response.data


if __name__ == "__main__":
    pytest.main()
