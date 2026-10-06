from typer.testing import CliRunner

from anibatch.cli.app import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AniBatch" in result.stdout
    assert "search" in result.stdout
    assert "download" in result.stdout
    assert "queue" in result.stdout
    assert "resume" in result.stdout
    assert "doctor" in result.stdout


def test_cli_doctor() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "System Diagnostics" in result.stdout
    assert "FFmpeg" in result.stdout


def test_cli_search() -> None:
    result = runner.invoke(app, ["search", "Frieren"])
    assert result.exit_code == 0
    assert "Searching for:" in result.stdout
    assert "Frieren" in result.stdout
