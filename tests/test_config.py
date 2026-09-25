from __future__ import annotations

from pathlib import Path

import pytest

from cdf.config import DEFAULT_IGNORE, default_config_paths, resolve_config
from cdf.errors import CdfError


@pytest.fixture(autouse=True)
def _isolate_default_config_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cdf.config.default_config_paths",
        lambda: (tmp_path / "unused-default-1.conf", tmp_path / "unused-default-2.conf"),
    )


def test_defaults_when_no_config_file() -> None:
    config = resolve_config()

    assert config.git is True
    assert config.hidden is False


def test_default_search_prefers_earlier_existing_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first.conf"
    second = tmp_path / "second.conf"
    first.write_text("git = false\n")
    second.write_text("git = true\n")
    monkeypatch.setattr("cdf.config.default_config_paths", lambda: (first, second))

    config = resolve_config()

    assert config.git is False


def test_default_search_falls_through_to_next_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first.conf"
    second = tmp_path / "second.conf"
    second.write_text("git = false\n")
    monkeypatch.setattr("cdf.config.default_config_paths", lambda: (first, second))

    config = resolve_config()

    assert config.git is False


def test_config_file_overrides_defaults(tmp_path: Path) -> None:
    search_root = tmp_path / "projects"
    search_root.mkdir()
    config_file = tmp_path / "cdf.conf"
    config_file.write_text(f'git = false\nhidden = true\npath = "{search_root}"\n')

    config = resolve_config(config_path=config_file)

    assert config.git is False
    assert config.hidden is True
    assert config.path == search_root


def test_cli_overrides_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text("git = false\n")

    config = resolve_config(config_path=config_file, cli_git=True)

    assert config.git is True


def test_invalid_toml_raises_cdf_error(tmp_path: Path) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text("not [ valid toml\n")

    with pytest.raises(CdfError, match="invalid config file"):
        resolve_config(config_path=config_file)


def test_unknown_key_raises_cdf_error(tmp_path: Path) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text("pathh = '/tmp'\n")

    with pytest.raises(CdfError, match="unknown key"):
        resolve_config(config_path=config_file)


def test_missing_search_root_raises_cdf_error(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    with pytest.raises(CdfError, match="does not exist"):
        resolve_config(cli_path=missing)


def test_non_bool_git_value_raises_cdf_error(tmp_path: Path) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text('git = "false"\n')

    with pytest.raises(CdfError, match="must be a boolean"):
        resolve_config(config_path=config_file)


def test_non_string_path_value_raises_cdf_error(tmp_path: Path) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text("path = 5\n")

    with pytest.raises(CdfError, match="must be a string"):
        resolve_config(config_path=config_file)


def test_explicit_missing_config_file_raises_cdf_error(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.conf"

    with pytest.raises(CdfError, match="config file not found"):
        resolve_config(config_path=missing)


def test_unreadable_config_file_raises_cdf_error(tmp_path: Path) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text("git = false\n")
    config_file.chmod(0o000)

    try:
        with pytest.raises(CdfError, match="cannot read config file"):
            resolve_config(config_path=config_file)
    finally:
        config_file.chmod(0o644)


def test_default_config_paths_prefer_xdg_config_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    assert default_config_paths() == (
        tmp_path / "xdg" / "cdf" / "cdf.conf",
        tmp_path / "home" / "cdf.conf",
    )


def test_default_config_paths_fall_back_to_dot_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert default_config_paths()[0] == tmp_path / ".config" / "cdf" / "cdf.conf"


def test_relative_config_path_is_relative_to_config_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "conf" / "projects").mkdir(parents=True)
    config_file = tmp_path / "conf" / "cdf.conf"
    config_file.write_text('path = "projects"\n')
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    config = resolve_config(config_path=config_file)

    assert config.path == tmp_path / "conf" / "projects"


def test_relative_cli_path_is_made_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "sub").mkdir()
    monkeypatch.chdir(tmp_path)

    config = resolve_config(cli_path=Path("sub/../sub"))

    assert config.path == tmp_path / "sub"


def test_default_root_is_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert resolve_config().path == tmp_path


def test_deleted_cwd_raises_cdf_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gone = tmp_path / "gone"
    gone.mkdir()
    monkeypatch.chdir(gone)
    gone.rmdir()

    with pytest.raises(CdfError, match="current directory no longer exists"):
        resolve_config()


def test_ignore_defaults_and_override(tmp_path: Path) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text('ignore = ["target", "*.egg-info"]\n')

    assert resolve_config().ignore == DEFAULT_IGNORE
    assert resolve_config(config_path=config_file).ignore == ("target", "*.egg-info")


@pytest.mark.parametrize("value", ['"node_modules"', "[1, 2]"])
def test_ignore_must_be_list_of_strings(tmp_path: Path, value: str) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text(f"ignore = {value}\n")

    with pytest.raises(CdfError, match="'ignore' must be a list of strings"):
        resolve_config(config_path=config_file)
