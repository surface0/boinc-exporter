import io
import os
from unittest.mock import patch

import pytest
from prometheus_client.core import CollectorRegistry

from boinc_exporter.boinc_client import Project, Task
from boinc_exporter.main import build_app


def _wsgi_env(path: str = "/metrics") -> dict:
    return {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "9101",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.StringIO(),
        "wsgi.url_scheme": "http",
        "HTTP_HOST": "localhost",
        "SERVER_PROTOCOL": "HTTP/1.1",
    }


def _call_app(app, path: str = "/metrics", *, tasks=None, projects=None):
    status_holder: list[str] = []
    headers_holder: list[dict] = []

    def start_response(status, headers, exc_info=None):
        status_holder.append(status)
        headers_holder.append(dict(headers))

    with patch("boinc_exporter.collector.BOINCClient") as MockClient:
        ctx = MockClient.return_value.__enter__.return_value
        ctx.get_tasks.return_value = tasks or []
        ctx.get_projects.return_value = projects or []
        body = b"".join(app(_wsgi_env(path), start_response))

    return status_holder[0], headers_holder[0], body.decode()


class TestBuildApp:
    def test_returns_callable(self):
        registry = CollectorRegistry()
        app = build_app(registry)
        assert callable(app)

    def test_uses_env_vars(self):
        registry = CollectorRegistry()
        env = {"BOINC_HOST": "192.168.1.10", "BOINC_PORT": "31417", "BOINC_PASSWORD": "pw"}
        with patch.dict(os.environ, env):
            with patch("boinc_exporter.collector.BOINCClient") as MockClient:
                MockClient.return_value.__enter__.return_value.get_tasks.return_value = []
                MockClient.return_value.__enter__.return_value.get_projects.return_value = []
                app = build_app(registry)
                app(_wsgi_env(), lambda s, h: None)
            call_kwargs = MockClient.call_args
        assert call_kwargs.args[0] == "192.168.1.10"
        assert call_kwargs.args[1] == 31417


class TestMetricsEndpoint:
    def setup_method(self):
        self.registry = CollectorRegistry()
        self.app = build_app(self.registry)

    def test_returns_200(self):
        status, _, _ = _call_app(self.app)
        assert status.startswith("200")

    def test_content_type_is_text_plain(self):
        _, headers, _ = _call_app(self.app)
        assert "text/plain" in headers.get("Content-Type", "")

    def test_contains_boinc_up(self):
        _, _, body = _call_app(self.app)
        assert "boinc_up" in body

    def test_boinc_up_is_1_when_connected(self):
        _, _, body = _call_app(
            self.app,
            tasks=[Task("t1", "http://x.org/", "files_downloaded", "executing", 0.5)],
            projects=[Project("WCG", "http://wcg.org/", 1000.0, 10.0, 50, 1)],
        )
        assert "boinc_up 1.0" in body

    def test_boinc_up_is_0_when_disconnected(self):
        with patch("boinc_exporter.collector.BOINCClient") as MockClient:
            MockClient.return_value.__enter__.side_effect = OSError("refused")
            _, _, body = b"".join(self.app(_wsgi_env(), lambda s, h: None)).decode(), None, None
        # Re-run properly
        status_holder: list[str] = []
        headers_holder: list[dict] = []
        with patch("boinc_exporter.collector.BOINCClient") as MockClient:
            MockClient.return_value.__enter__.side_effect = OSError("refused")
            body = b"".join(self.app(_wsgi_env(), lambda s, h: (status_holder.append(s), headers_holder.append(h)))).decode()
        assert "boinc_up 0.0" in body

    def test_task_metrics_present(self):
        _, _, body = _call_app(
            self.app,
            tasks=[Task("t1", "http://x.org/", "files_downloaded", "executing", 0.6)],
        )
        assert "boinc_tasks_total" in body
        assert "boinc_task_fraction_done" in body

    def test_project_metrics_present(self):
        _, _, body = _call_app(
            self.app,
            projects=[Project("WCG", "http://wcg.org/", 2000.0, 25.0, 100, 3)],
        )
        assert "boinc_project_total_credit" in body
        assert 'project="WCG"' in body
