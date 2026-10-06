"""REST API server and async bridge for the AniBatch local web dashboard."""

import asyncio
import http.server
import json
import logging
import threading
import urllib.parse
import webbrowser
from collections.abc import Coroutine
from pathlib import Path
from typing import Any, TypeVar

from anibatch.providers.registry import init_default_providers, registry
from anibatch.services.download_service import DownloadService

logger = logging.getLogger("anibatch.web")

T = TypeVar("T")


class _AniBatchThreadingHTTPServer(http.server.ThreadingHTTPServer):
    """Custom ThreadingHTTPServer keeping a reference to the AniBatchWebServer."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[http.server.BaseHTTPRequestHandler],
        web_server: "AniBatchWebServer",
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.web_server = web_server


class _AniBatchRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler implementing REST API endpoints and static HTML delivery."""

    server: _AniBatchThreadingHTTPServer

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard stderr access logging to keep terminal logs clean."""
        logger.debug(
            "%s - - [%s] %s",
            self.address_string(),
            self.log_date_time_string(),
            format % args,
        )

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status=status)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _parse_json_body(self) -> dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                return {}
            raw = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
            return {}
        except (ValueError, UnicodeDecodeError):
            return {}

    def _run_async(self, coro: Coroutine[Any, Any, T], timeout: float = 30.0) -> T:
        future = asyncio.run_coroutine_threadsafe(coro, self.server.web_server.loop)
        return future.result(timeout=timeout)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            self._handle_get_root()
            return

        if parsed.path == "/api/providers":
            self._handle_get_providers()
            return

        if parsed.path == "/api/search":
            self._handle_get_search(params)
            return

        if parsed.path == "/api/info":
            self._handle_get_info(params)
            return

        if parsed.path == "/api/queue":
            self._handle_get_queue()
            return

        self._send_error_json("Not Found", 404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/download":
            self._handle_post_download()
            return

        if parsed.path == "/api/queue/pause":
            self._handle_post_queue_pause()
            return

        if parsed.path == "/api/queue/resume":
            self._handle_post_queue_resume()
            return

        if parsed.path == "/api/queue/cancel":
            self._handle_post_queue_cancel()
            return

        self._send_error_json("Not Found", 404)

    def _handle_get_root(self) -> None:
        static_file = Path(__file__).parent / "static" / "index.html"
        if static_file.exists():
            html_text = static_file.read_text(encoding="utf-8")
        else:
            html_text = (
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\">\n"
                "  <title>AniBatch Dashboard</title>\n"
                "</head>\n"
                "<body>\n"
                "  <h1>AniBatch</h1>\n"
                "  <p>Download Queue</p>\n"
                "</body>\n"
                "</html>"
            )
        self._send_html(html_text)

    def _handle_get_providers(self) -> None:
        init_default_providers()
        provs = []
        for name in registry.list_available():
            p = registry.get(name)
            if p:
                provs.append(
                    {
                        "name": p.name,
                        "capabilities": p.capabilities.model_dump(mode="json"),
                    }
                )
        self._send_json(provs)

    def _handle_get_search(self, params: dict[str, list[str]]) -> None:
        query = params.get("q", [""])[0]
        provider = params.get("provider", [None])[0]
        service = self.server.web_server.service

        async def _search() -> list[dict[str, Any]]:
            try:
                return await service.search(query, provider=provider)  # type: ignore[call-arg]
            except TypeError:
                pass

            if provider and provider not in ("all", "anilist"):
                init_default_providers()
                prov_inst = registry.get(provider)
                if prov_inst:
                    try:
                        p_results = await prov_inst.search(query)
                        return [
                            {
                                "id": ps.id,
                                "title": ps.title,
                                "year": ps.year,
                                "episodes": ps.episode_count,
                                "source": provider,
                            }
                            for ps in p_results
                        ]
                    except Exception:  # noqa: BLE001
                        return []
                return []

            return await service.search(query)

        try:
            results = self._run_async(_search())
            self._send_json(results)
        except Exception as e:  # noqa: BLE001
            self._send_error_json(str(e), 500)

    def _handle_get_info(self, params: dict[str, list[str]]) -> None:
        series_id = params.get("id", [""])[0]
        provider = params.get("provider", ["test"])[0]
        service = self.server.web_server.service

        async def _info() -> dict[str, Any]:
            try:
                return await service.get_series_info(series_id, provider=provider)  # type: ignore[call-arg]
            except TypeError:
                return await service.get_series_info(series_id, provider_name=provider)

        try:
            info = self._run_async(_info())
            self._send_json(info)
        except Exception as e:  # noqa: BLE001
            self._send_error_json(str(e), 500)

    def _handle_get_queue(self) -> None:
        service = self.server.web_server.service

        async def _queue() -> list[Any]:
            if hasattr(service, "get_queue"):
                return await service.get_queue()
            return await service.list_jobs()

        try:
            jobs = self._run_async(_queue())
            serialized = [
                j.model_dump(mode="json") if hasattr(j, "model_dump") else j for j in jobs
            ]
            self._send_json(serialized)
        except Exception as e:  # noqa: BLE001
            self._send_error_json(str(e), 500)

    def _handle_post_download(self) -> None:
        data = self._parse_json_body()
        series_id = str(data.get("series_id", ""))
        if not series_id:
            self._send_error_json("Missing 'series_id'", 400)
            return

        episodes = str(data.get("episodes", "all"))
        provider = str(data.get("provider", "test"))
        quality = str(data.get("quality", "1080p"))
        service = self.server.web_server.service

        async def _enqueue() -> list[str]:
            if hasattr(service, "enqueue_batch"):
                return await service.enqueue_batch(
                    series_id=series_id,
                    episodes=episodes,
                    quality=quality,
                    provider=provider,
                )
            return await service.queue_episodes(
                series_id=series_id,
                episode_range=episodes,
                quality=quality,
                provider_name=provider,
            )

        try:
            job_ids = self._run_async(_enqueue())
            self._send_json({"queued_count": len(job_ids), "job_ids": job_ids})
        except Exception as e:  # noqa: BLE001
            self._send_error_json(str(e), 500)

    def _handle_post_queue_pause(self) -> None:
        data = self._parse_json_body()
        job_id = data.get("job_id")
        service = self.server.web_server.service

        async def _pause() -> Any:
            if job_id:
                await service.pause_job(str(job_id))
                return {"status": "paused", "job_id": job_id}
            if hasattr(service, "pause_queue"):
                count = await service.pause_queue()
                return {"status": "paused", "count": count}
            jobs = await service.list_jobs()
            count = 0
            for j in jobs:
                if getattr(j.state, "value", str(j.state)) == "queued":
                    await service.pause_job(j.id)
                    count += 1
            return {"status": "paused", "count": count}

        try:
            res = self._run_async(_pause())
            self._send_json(res)
        except Exception as e:  # noqa: BLE001
            self._send_error_json(str(e), 500)

    def _handle_post_queue_resume(self) -> None:
        service = self.server.web_server.service

        async def _resume() -> Any:
            if hasattr(service, "resume_queue"):
                count = await service.resume_queue()
            else:
                count = await service.resume_all()
            return {"status": "resumed", "count": count}

        try:
            res = self._run_async(_resume())
            self._send_json(res)
        except Exception as e:  # noqa: BLE001
            self._send_error_json(str(e), 500)

    def _handle_post_queue_cancel(self) -> None:
        data = self._parse_json_body()
        job_id = data.get("job_id")
        if not job_id:
            self._send_error_json("Missing 'job_id'", 400)
            return

        service = self.server.web_server.service

        async def _cancel() -> None:
            await service.cancel_job(str(job_id))

        try:
            self._run_async(_cancel())
            self._send_json({"status": "cancelled", "job_id": job_id})
        except Exception as e:  # noqa: BLE001
            self._send_error_json(str(e), 500)


class AniBatchWebServer:
    """Zero-dependency local HTTP web server and async bridge for AniBatch."""

    def __init__(
        self,
        service: DownloadService | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        self.service = service or DownloadService()
        self.host = host
        self.port = port
        self.server_port = port

        self._server: _AniBatchThreadingHTTPServer | None = None
        self._server_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._is_running = False

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            raise RuntimeError("Event loop is not running. Call start() first.")
        return self._loop

    def start(self, open_browser: bool = False) -> None:
        """Start the background event loop and HTTP server."""
        if self._is_running:
            return

        # 1. Start dedicated background asyncio loop
        self._loop = asyncio.new_event_loop()

        def _run_loop(loop: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._loop_thread = threading.Thread(
            target=_run_loop,
            args=(self._loop,),
            name="AniBatchAsyncLoop",
            daemon=True,
        )
        self._loop_thread.start()

        # 2. Start ThreadingHTTPServer
        self._server = _AniBatchThreadingHTTPServer(
            (self.host, self.port),
            _AniBatchRequestHandler,
            self,
        )
        # Store actual bound port (in case port was 0)
        self.server_port = self._server.server_address[1]

        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name="AniBatchWebServer",
            daemon=True,
        )
        self._server_thread.start()
        self._is_running = True

        logger.info("AniBatch web server running at http://%s:%d", self.host, self.server_port)

        if open_browser:
            webbrowser.open(f"http://{self.host}:{self.server_port}")

    def stop(self) -> None:
        """Cleanly shut down HTTP server and background event loop."""
        if not self._is_running:
            return

        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)
            self._server_thread = None

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=2.0)
            self._loop_thread = None

        if self._loop and not self._loop.is_closed():
            self._loop.close()
            self._loop = None

        self._is_running = False
