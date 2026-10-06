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
    assert "pause" in result.stdout
    assert "resume" in result.stdout
    assert "cancel" in result.stdout
    assert "history" in result.stdout
    assert "providers" in result.stdout
    assert "doctor" in result.stdout
    assert "config" in result.stdout


def test_cli_search_local_provider() -> None:
    result = runner.invoke(app, ["search", "Frieren"])
    assert result.exit_code == 0
    assert "Frieren" in result.stdout


def test_cli_info() -> None:
    result = runner.invoke(app, ["info", "fake-frieren"])
    assert result.exit_code == 0
    assert "Frieren: Beyond Journey's End" in result.stdout
    assert "Available Episodes (12)" in result.stdout


def test_cli_download_batch() -> None:
    result = runner.invoke(app, ["download", "fake-frieren", "--episodes", "1-3"])
    assert result.exit_code == 0
    assert "Successfully queued 3 episode(s)" in result.stdout


def test_cli_queue_and_pause_resume() -> None:
    # First inspect queue
    q_res = runner.invoke(app, ["queue"])
    assert q_res.exit_code == 0

    # Pause a job
    p_res = runner.invoke(app, ["pause", "job-fake-frieren-01"])
    assert p_res.exit_code == 0
    assert "paused" in p_res.stdout.lower()

    # Resume
    r_res = runner.invoke(app, ["resume"])
    assert r_res.exit_code == 0
    assert "Resumed" in r_res.stdout


def test_cli_cancel() -> None:
    c_res = runner.invoke(app, ["cancel", "job-fake-frieren-02"])
    assert c_res.exit_code == 0
    assert "cancelled" in c_res.stdout.lower()


def test_cli_history() -> None:
    h_res = runner.invoke(app, ["history"])
    assert h_res.exit_code == 0


def test_cli_providers() -> None:
    prov_res = runner.invoke(app, ["providers"])
    assert prov_res.exit_code == 0
    assert "test" in prov_res.stdout
    assert "Online" in prov_res.stdout


def test_cli_config() -> None:
    cfg_res = runner.invoke(app, ["config"])
    assert cfg_res.exit_code == 0
    assert "Download Directory" in cfg_res.stdout
    assert "Concurrency" in cfg_res.stdout


def test_cli_doctor() -> None:
    doc_res = runner.invoke(app, ["doctor"])
    assert doc_res.exit_code == 0
    assert "System Diagnostics" in doc_res.stdout
    assert "FFmpeg" in doc_res.stdout
    assert "Database" in doc_res.stdout
