import argparse
import pytest
import subprocess
import os
from typing import Tuple, List

# Define the paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_SCRIPT_PATH = os.path.join(BASE_DIR, "src", "gpxtable", "cli.py")


def _run_cli(args: List[str]):
    env = os.environ.copy()
    env["TZ"] = "America/Los_Angeles"
    return subprocess.run(
        ["python", CLI_SCRIPT_PATH] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


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
    ("basecamp-route", []),
    ("basecamp-tracks", ["--depart", "07/30/2022 09:15:00"]),
    ("scenic2", ["--depart", "07/30/2023 09:15:00"]),
    ("ich-north-fixed", ["--depart", "07/30/2023 09:15:00"]),
]


def input_output_names(filename: str) -> Tuple[str, str]:
    # sourcery skip: use-fstring-for-concatenation
    return (
        os.path.join(BASE_DIR, "samples", filename + ".gpx"),
        os.path.join(BASE_DIR, "samples", filename + ".txt"),
    )


@pytest.mark.parametrize(("test_case", "arguments"), file_test_cases)
def test_cli_files_parm(run_cli, test_case: str, arguments: list):
    input_file, expected_file = input_output_names(test_case)
    args = arguments + [input_file]
    result = run_cli(args)
    assert result.returncode == 0
    with open(expected_file, "r") as f:
        expected_output = f.read()
    assert result.stdout == expected_output


def test_bad_xml(run_cli) -> None:
    input_file, _ = input_output_names("bad-xml")
    result = run_cli([input_file])
    assert result.returncode != 0
    assert "Error parsing XML" in result.stderr


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
