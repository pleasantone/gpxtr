import os
import io
import pytest
from gpxtable.wsgi import app

TEST_FILE = "samples/basecamp.gpx"
TEST_RESPONSE = b"Garmin Desktop App"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def test_index(client):
    """Test the index page."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"URL to GPX file" in response.data


def test_upload_file(client):
    """Test file upload."""
    data = {"file": (open(TEST_FILE, "rb"), os.path.dirname(TEST_FILE))}
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert TEST_RESPONSE in response.data


def test_upload_url(client, monkeypatch):
    """Test URL submission."""

    # Mock the requests.get call to return a dummy response
    class MockResponse:
        def __init__(self, content, status_code):
            self.content = content
            self.status_code = status_code

    def mock_get(*args, **kwargs):
        with open(TEST_FILE, "rb") as f:
            return MockResponse(f.read(), 200)

    monkeypatch.setattr("requests.get", mock_get)

    data = {"url": "http://example.com/test.gpx"}
    response = client.post("/", data=data)
    assert response.status_code == 200
    assert TEST_RESPONSE in response.data


if __name__ == "__main__":
    pytest.main()
