from _pytest._py.path import LocalPath
import argparse
import pytest
import subprocess
import os
from unittest import mock

# Define the paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_SCRIPT_PATH = os.path.join(BASE_DIR, "src", "gpxtable", "cli.py")


@pytest.fixture
def set_environment_variables(monkeypatch: pytest.MonkeyPatch):
    env_vars = {
        "TZ": "America/Los_Angeles",
    }
    with mock.patch.dict(os.environ, env_vars, clear=True):
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        yield  # This is the magical bit which restore the environment after


def _run_cli(args):
    env = os.environ.copy()
    env["TZ"] = "America/Los_Angeles"
    result = subprocess.run(
        ["python", CLI_SCRIPT_PATH] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    return result


@pytest.fixture
def run_cli():
    return _run_cli


def test_cli_help(run_cli):
    result = run_cli(["--help"])
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_cli_invalid_file(run_cli):
    result = run_cli(["non_existent_file.gpx"])
    assert result.returncode != 0
    assert "Errno" in result.stderr


file_test_cases = [
    ("basecamp", ["--depart", "07/30/2023 09:15:00"]),
    ("scenic2", ["--depart", "07/30/2023 09:15:00"]),
    ("ich-north-fixed", ["--depart", "07/30/2023 09:15:00"]),
]


def input_output_names(filename: str):
    return (
        os.path.join(BASE_DIR, "samples", filename + ".gpx"),
        os.path.join(BASE_DIR, "samples", filename + ".md"),
    )


@pytest.mark.parametrize("test_case,arguments", file_test_cases)
def test_cli_files_parm(test_case: str, arguments: list):
    input_file, expected_file = input_output_names(test_case)
    args = arguments + [input_file]
    result = _run_cli(args)
    assert result.returncode == 0
    with open(expected_file, "r") as f:
        expected_output = f.read()
    assert result.stdout == expected_output


def generate_sample_output() -> None:
    for test_case, arguments in file_test_cases:
        input_file, output_file = input_output_names(test_case)
        args = arguments + [input_file]
        print(f"gpxtable {' '.join(args)} > {output_file}...")
        result = _run_cli(args)
        assert result.returncode == 0
        with open(output_file, "w") as f:
            f.write(result.stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate", action="store_true", help="generate expected output files"
    )
    try:
        args = parser.parse_args()
    except ValueError as err:
        raise SystemExit(err) from err

    if args.generate:
        generate_sample_output()
    else:
        pytest.main()
