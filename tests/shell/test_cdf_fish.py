from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from cdf.cli import shell_init_script

pytestmark = pytest.mark.skipif(shutil.which("fish") is None, reason="fish not installed")

# Stands in for the real `cdf` binary: prints $FAKE_CDF_OUT, exits $FAKE_CDF_CODE.
_FAKE_CDF = """#!/bin/sh
printf '%s\\n' "$FAKE_CDF_OUT"
exit "${FAKE_CDF_CODE:-0}"
"""


def _run_wrapper(
    tmp_path: Path, args: str, *, out: str, code: int = 0
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "cdf"
    fake.write_text(_FAKE_CDF)
    fake.chmod(0o755)
    wrapper = tmp_path / "cdf.fish"
    wrapper.write_text(shell_init_script("fish"))
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_CDF_OUT": out,
        "FAKE_CDF_CODE": str(code),
        "CDPATH": str(tmp_path / "cdpath"),
    }
    script = f'source "{wrapper}"; cdf {args}; echo "status=$status"; pwd'
    return subprocess.run(
        ["fish", "--no-config", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


def test_cds_into_selected_directory(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()

    result = _run_wrapper(tmp_path, "term", out=str(target))

    assert result.stdout.splitlines() == ["status=0", str(target)]


def test_target_containing_newline_survives(tmp_path: Path) -> None:
    target = tmp_path / "a\nb"
    target.mkdir()

    result = _run_wrapper(tmp_path, "", out=str(target))

    assert result.stdout == f"status=0\n{target}\n"


def test_target_starting_with_dash_is_not_an_option(tmp_path: Path) -> None:
    (tmp_path / "-L").mkdir()

    result = _run_wrapper(tmp_path, "", out="-L")

    assert result.stdout.splitlines() == ["status=0", str(tmp_path / "-L")]


def test_stays_put_when_nothing_selected(tmp_path: Path) -> None:
    result = _run_wrapper(tmp_path, "", out="", code=1)

    assert result.stdout.splitlines() == ["status=1", str(tmp_path)]


@pytest.mark.parametrize("flag", ["--help", "-h", "--version", "--init fish", "--init=fish"])
def test_informational_flags_pass_through(tmp_path: Path, flag: str) -> None:
    result = _run_wrapper(tmp_path, flag, out="some text\nmore text")

    assert result.stdout.splitlines() == ["some text", "more text", "status=0", str(tmp_path)]
    assert result.stderr == ""
