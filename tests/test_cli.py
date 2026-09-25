from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

from cdf import cli
from cdf.errors import CdfError, NoCandidatesError


@pytest.fixture(autouse=True)
def _clear_cdf_config_path_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CDF_CONFIG_PATH", raising=False)


@pytest.fixture(autouse=True)
def _isolate_default_config_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cdf.config.default_config_paths",
        lambda: (tmp_path / "unused-default-1.conf", tmp_path / "unused-default-2.conf"),
    )


def test_prints_resolved_path_to_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "repo"
    monkeypatch.setattr(cli, "resolve", lambda *args, **kwargs: target)

    exit_code = cli.main(["term", "--path", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == f"{target}\n"
    assert captured.err == ""


def test_returns_one_when_nothing_selected(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "resolve", lambda *args, **kwargs: None)

    exit_code = cli.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""


def test_no_git_flag_disables_git_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, object] = {}

    def fake_resolve(term: str, root: Path, **kwargs: object) -> Path | None:
        captured_kwargs.update(kwargs)
        return None

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    cli.main(["--no-git", "--path", str(tmp_path)])

    assert captured_kwargs["git_only"] is False


def test_no_all_flag_overrides_config_hidden_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text("hidden = true\n")
    captured_kwargs: dict[str, object] = {}

    def fake_resolve(term: str, root: Path, **kwargs: object) -> Path | None:
        captured_kwargs.update(kwargs)
        return None

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    cli.main(["--no-all", "--path", str(tmp_path), "--config", str(config_file)])

    assert captured_kwargs["include_hidden"] is False


def test_explicit_missing_config_file_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "does-not-exist.conf"

    exit_code = cli.main(["--path", str(tmp_path), "--config", str(missing)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "config file not found" in captured.err


def test_default_missing_config_file_is_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_kwargs: dict[str, object] = {}

    def fake_resolve(term: str, root: Path, **kwargs: object) -> Path | None:
        captured_kwargs.update(kwargs)
        return None

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    exit_code = cli.main(["--path", str(tmp_path)])

    assert exit_code == 1
    assert captured_kwargs["git_only"] is True


def test_env_var_sets_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "custom.conf"
    config_file.write_text("hidden = true\n")
    monkeypatch.setenv("CDF_CONFIG_PATH", str(config_file))
    captured_kwargs: dict[str, object] = {}

    def fake_resolve(term: str, root: Path, **kwargs: object) -> Path | None:
        captured_kwargs.update(kwargs)
        return None

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    cli.main(["--path", str(tmp_path)])

    assert captured_kwargs["include_hidden"] is True


def test_cli_flag_overrides_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_config = tmp_path / "env.conf"
    env_config.write_text("hidden = true\n")
    cli_config = tmp_path / "cli.conf"
    cli_config.write_text("hidden = false\n")
    monkeypatch.setenv("CDF_CONFIG_PATH", str(env_config))
    captured_kwargs: dict[str, object] = {}

    def fake_resolve(term: str, root: Path, **kwargs: object) -> Path | None:
        captured_kwargs.update(kwargs)
        return None

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    cli.main(["--path", str(tmp_path), "--config", str(cli_config)])

    assert captured_kwargs["include_hidden"] is False


def test_empty_env_var_is_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CDF_CONFIG_PATH", "")
    captured_kwargs: dict[str, object] = {}

    def fake_resolve(term: str, root: Path, **kwargs: object) -> Path | None:
        captured_kwargs.update(kwargs)
        return None

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    exit_code = cli.main(["--path", str(tmp_path)])

    assert exit_code == 1
    assert captured_kwargs["git_only"] is True


def test_cdf_error_prints_to_stderr_and_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_resolve(*args: object, **kwargs: object) -> Path | None:
        raise CdfError("boom")

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    exit_code = cli.main(["--path", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "boom\n"


def test_version_flag_prints_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])

    assert exc_info.value.code == 0
    assert "cdf" in capsys.readouterr().out


def test_version_flag_falls_back_when_package_metadata_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def raise_not_found(name: str) -> str:
        raise PackageNotFoundError(name)

    monkeypatch.setattr(cli, "version", raise_not_found)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])

    assert exc_info.value.code == 0
    assert "unknown" in capsys.readouterr().out


def test_multiple_term_words_are_joined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured_terms: list[str] = []

    def fake_resolve(term: str, root: Path, **kwargs: object) -> Path | None:
        captured_terms.append(term)
        return None

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    cli.main(["foo", "bar", "--path", str(tmp_path)])

    assert captured_terms == ["foo bar"]


def test_config_ignore_reaches_resolve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "cdf.conf"
    config_file.write_text('ignore = ["target"]\n')
    captured_kwargs: dict[str, object] = {}

    def fake_resolve(term: str, root: Path, **kwargs: object) -> Path | None:
        captured_kwargs.update(kwargs)
        return None

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    cli.main(["--path", str(tmp_path), "--config", str(config_file)])

    assert captured_kwargs["ignore"] == ("target",)


def test_no_candidates_prints_hint_and_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_resolve(*args: object, **kwargs: object) -> Path | None:
        raise NoCandidatesError("no git repositories found")

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    exit_code = cli.main(["--path", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "no git repositories found\n"


def test_keyboard_interrupt_exits_130_quietly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_resolve(*args: object, **kwargs: object) -> Path | None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "resolve", fake_resolve)

    exit_code = cli.main(["--path", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 130
    assert captured.out == ""


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_init_prints_shell_wrapper(shell: str, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--init", shell])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "cdf() {" in out
    assert 'cd -- "$target"' in out


def test_init_rejects_unknown_shell(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--init", "tcsh"])

    assert exc_info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_init_fish_prints_fish_wrapper(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--init", "fish"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert out.startswith("# cdf shell integration for fish")
    assert "function cdf" in out


@pytest.mark.parametrize("abbreviation", ["--ver", "--he", "--in"])
def test_long_options_cannot_be_abbreviated(
    abbreviation: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main([abbreviation])

    assert exc_info.value.code == 2
    assert capsys.readouterr().out == ""


def test_help_lists_none_when_no_default_config_paths(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "default_config_paths", lambda: ())

    with pytest.raises(SystemExit):
        cli.main(["--help"])

    assert "first existing of none" in " ".join(capsys.readouterr().out.split())
