import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from anibatch.services.download_service import DownloadService
from anibatch.web.server import AniBatchWebServer


@pytest.fixture
def web_server(tmp_path: Path):
    service = DownloadService(db_path=tmp_path / "web_test.db")
    server = AniBatchWebServer(service=service, host="127.0.0.1", port=0)
    server.start(open_browser=False)
    yield server
    server.stop()


def test_api_providers(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/providers")
    assert req.status == 200
    assert "application/json" in req.headers.get("Content-Type", "")
    data = json.loads(req.read().decode())
    assert isinstance(data, list)
    assert any(p.get("name") == "test" for p in data)


def test_api_search(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/search?q=Frieren&provider=test")
    assert req.status == 200
    data = json.loads(req.read().decode())
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any("Frieren" in item.get("title", "") for item in data)


def test_api_info(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/info?id=fake-frieren&provider=test")
    assert req.status == 200
    data = json.loads(req.read().decode())
    assert data.get("id") == "fake-frieren"
    assert "Frieren" in data.get("title", "")
    assert len(data.get("episodes", [])) == 12


def test_api_download_and_queue(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port

    # 1. Enqueue job
    payload = json.dumps({"series_id": "fake-frieren", "episodes": "1", "provider": "test"}).encode()
    post_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/download",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(post_req)
    assert resp.status == 200
    res_data = json.loads(resp.read().decode())
    assert res_data.get("queued_count") == 1

    # 2. Get queue
    q_req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/queue")
    assert q_req.status == 200
    q_data = json.loads(q_req.read().decode())
    assert isinstance(q_data, list)
    assert len(q_data) >= 1
    job = next(j for j in q_data if j["id"] == "job-fake-frieren-01")
    assert job["state"] == "queued"


def test_api_queue_pause_resume_cancel(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port

    # Enqueue a job
    payload = json.dumps({"series_id": "fake-frieren", "episodes": "1", "provider": "test"}).encode()
    post_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/download",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(post_req)

    # Pause specific job
    pause_payload = json.dumps({"job_id": "job-fake-frieren-01"}).encode()
    pause_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/queue/pause",
        data=pause_payload,
        headers={"Content-Type": "application/json"},
    )
    pause_resp = urllib.request.urlopen(pause_req)
    assert pause_resp.status == 200

    q_data = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/queue").read().decode())
    job = next(j for j in q_data if j["id"] == "job-fake-frieren-01")
    assert job["state"] == "paused"

    # Resume queue
    resume_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/queue/resume",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    resume_resp = urllib.request.urlopen(resume_req)
    assert resume_resp.status == 200

    q_data = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/queue").read().decode())
    job = next(j for j in q_data if j["id"] == "job-fake-frieren-01")
    assert job["state"] == "queued"

    # Pause entire queue (no job_id)
    pause_all_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/queue/pause",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    pause_all_resp = urllib.request.urlopen(pause_all_req)
    assert pause_all_resp.status == 200

    # Cancel job
    cancel_payload = json.dumps({"job_id": "job-fake-frieren-01"}).encode()
    cancel_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/queue/cancel",
        data=cancel_payload,
        headers={"Content-Type": "application/json"},
    )
    cancel_resp = urllib.request.urlopen(cancel_req)
    assert cancel_resp.status == 200

    q_data = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/queue").read().decode())
    job = next(j for j in q_data if j["id"] == "job-fake-frieren-01")
    assert job["state"] == "cancelled"


def test_api_cancel_missing_job_id(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    cancel_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/queue/cancel",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(cancel_req)
    assert exc_info.value.code == 400


def test_serve_dashboard_html(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/")
    assert req.status == 200
    assert "text/html" in req.headers.get("Content-Type", "")
    content = req.read().decode()
    assert "AniBatch" in content
    assert "Download Queue" in content
    assert "Search Results" in content
    assert "episodeModal" in content


def test_favicon_handled(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico")
    assert req.status == 204


def test_not_found(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/nonexistent")
    assert exc_info.value.code == 404


def test_api_download_missing_series_id(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    post_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/download",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(post_req)
    assert exc_info.value.code == 400


def test_cors_options_request(web_server: AniBatchWebServer) -> None:
    port = web_server.server_port
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/queue",
        method="OPTIONS",
    )
    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "*"


def test_server_lifecycle_and_loop_property(tmp_path: Path) -> None:
    server = AniBatchWebServer(service=DownloadService(db_path=tmp_path / "life.db"), port=0)
    # Loop accessed before start raises RuntimeError
    with pytest.raises(RuntimeError):
        _ = server.loop

    server.start(open_browser=False)
    assert server.loop.is_running()
    # Idempotent start
    server.start(open_browser=False)

    server.stop()
    # Idempotent stop
    server.stop()

