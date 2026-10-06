import pytest
import respx
from typer.testing import CliRunner

from anibatch.cli.app import app
from anibatch.services.download_service import DownloadService

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
    assert "web" in result.stdout



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


def test_cli_doctor(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("https://graphql.anilist.co").respond(200, json={"data": {"Page": {"media": [{"id": 1}]}}})
    respx_mock.get("https://archive.org/advancedsearch.php").respond(200, json={"response": {"docs": []}})
    doc_res = runner.invoke(app, ["doctor"])
    assert doc_res.exit_code == 0
    assert "System Diagnostics" in doc_res.stdout
    assert "FFmpeg" in doc_res.stdout
    assert "Database" in doc_res.stdout
    assert "[OK] AniList: Reachable" in doc_res.stdout
    assert "Provider (test): Online" in doc_res.stdout
    assert "Provider (archive): Online" in doc_res.stdout


def test_cli_doctor_offline(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("https://graphql.anilist.co").respond(500)
    respx_mock.get("https://archive.org/advancedsearch.php").respond(200, json={"response": {"docs": []}})
    doc_res = runner.invoke(app, ["doctor"])
    assert doc_res.exit_code == 0
    assert "[!] AniList: Offline / No internet" in doc_res.stdout


@pytest.mark.asyncio
async def test_download_service_run_diagnostics(respx_mock: respx.MockRouter) -> None:
    respx_mock.post("https://graphql.anilist.co").respond(200, json={"data": {"Page": {"media": [{"id": 1}]}}})
    respx_mock.get("https://archive.org/advancedsearch.php").respond(200, json={"response": {"docs": []}})
    service = DownloadService()
    diag = await service.run_diagnostics()
    assert diag["anilist_reachable"] is True
    assert diag["providers"]["test"] is True
    assert diag["providers"]["archive"] is True

    # Test error/offline branch
    respx_mock.reset()
    respx_mock.post("https://graphql.anilist.co").respond(500)
    respx_mock.get("https://archive.org/advancedsearch.php").respond(500)
    diag_offline = await service.run_diagnostics()
    assert diag_offline["anilist_reachable"] is False
    assert diag_offline["providers"]["archive"] is False


def test_cli_json_flags() -> None:
    res = runner.invoke(app, ["search", "Frieren", "--json"])
    assert res.exit_code == 0
    assert "[" in res.stdout
    assert "Frieren" in res.stdout

    q_res = runner.invoke(app, ["queue", "--json"])
    assert q_res.exit_code == 0
    assert "[" in q_res.stdout


def test_cli_export_and_import_queue(tmp_path) -> None:
    export_file = tmp_path / "queue_export.json"
    res_exp = runner.invoke(app, ["export-queue", str(export_file)])
    assert res_exp.exit_code == 0
    assert export_file.exists()

    res_imp = runner.invoke(app, ["import-queue", str(export_file)])
    assert res_imp.exit_code == 0
    assert "Imported" in res_imp.stdout


def test_cli_web_help() -> None:
    result = runner.invoke(app, ["web", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--no-browser" in result.stdout

