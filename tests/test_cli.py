import pytest
import subprocess
import os
from unittest import mock

# Define the paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_SCRIPT_PATH = os.path.join(BASE_DIR, "src", "gpxtable", "cli.py")
GPX_FILE_PATH = os.path.join(BASE_DIR, "samples", "basecamp.gpx")
GPX_OUTPUT_PATH = os.path.join(BASE_DIR, "samples", "basecamp.md")


@pytest.fixture()
def setenvvar(monkeypatch):
    with mock.patch.dict(os.environ, clear=True):
        envvars = {
            "TZ": "America/Los_Angeles",
        }
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield  # This is the magical bit which restore the environment after


@pytest.fixture
def run_cli(tmpdir):
    def _run_cli(args):
        my_env = os.environ.copy()
        my_env["TZ"] = "America/Los_Angeles"
        result = subprocess.run(
            ["python", CLI_SCRIPT_PATH] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=my_env,
        )
        return result

    return _run_cli


def test_cli_help(run_cli):
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_cli_output(run_cli, tmpdir):
    output_file = tmpdir.join("output.md")
    result = run_cli(
        ["-o", str(output_file), "--depart", "07/30/2023 09:15:00", GPX_FILE_PATH]
    )
    assert result.returncode == 0
    with open(GPX_OUTPUT_PATH, "r") as f:
        expected_output = f.read()
    with open(output_file, "r") as f:
        actual_output = f.read()
    assert actual_output == expected_output


def test_cli_basecamp(run_cli):
    with open(GPX_OUTPUT_PATH, "r") as f:
        expected_output = f.read()
    result = run_cli(["--depart", "07/30/2023 09:15:00", GPX_FILE_PATH])
    assert result.returncode == 0
    assert result.stdout == expected_output


def test_cli_invalid_file(run_cli):
    result = run_cli(["non_existent_file.gpx"])
    assert result.returncode != 0
    assert "Errno" in result.stderr


if __name__ == "__main__":
    pytest.main()
