from unittest.mock import patch

import pytest
from prometheus_client.core import CollectorRegistry

from boinc_exporter.boinc_client import Project, Task
from boinc_exporter.collector import BOINCCollector


def _make_collector() -> BOINCCollector:
    return BOINCCollector(host="localhost", port=31416, password="")


def _collect(collector: BOINCCollector) -> dict:
    return {m.name: m for m in collector.collect()}


def _mock_client(tasks: list, projects: list):
    """Context manager that patches BOINCClient to return given tasks and projects."""
    mock = patch("boinc_exporter.collector.BOINCClient")
    patcher = mock.start()
    ctx = patcher.return_value.__enter__.return_value
    ctx.get_tasks.return_value = tasks
    ctx.get_projects.return_value = projects
    return patcher, mock


class TestBOINCUp:
    def test_up_when_reachable(self):
        with patch("boinc_exporter.collector.BOINCClient") as MockClient:
            MockClient.return_value.__enter__.return_value.get_tasks.return_value = []
            MockClient.return_value.__enter__.return_value.get_projects.return_value = []
            metrics = _collect(_make_collector())
        assert metrics["boinc_up"].samples[0].value == 1.0

    def test_down_on_connection_error(self):
        with patch("boinc_exporter.collector.BOINCClient") as MockClient:
            MockClient.return_value.__enter__.side_effect = OSError("connection refused")
            metrics = _collect(_make_collector())
        assert metrics["boinc_up"].samples[0].value == 0.0

    def test_no_other_metrics_when_down(self):
        with patch("boinc_exporter.collector.BOINCClient") as MockClient:
            MockClient.return_value.__enter__.side_effect = OSError("refused")
            metrics = _collect(_make_collector())
        assert set(metrics.keys()) == {"boinc_up"}


class TestTaskMetrics:
    def _run(self, tasks: list, projects: list | None = None) -> dict:
        with patch("boinc_exporter.collector.BOINCClient") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get_tasks.return_value = tasks
            ctx.get_projects.return_value = projects or []
            return _collect(_make_collector())

    def test_executing_task_counted(self):
        tasks = [Task("t1", "http://x.org/", "files_downloaded", "executing", 0.5)]
        metrics = self._run(tasks)
        states = {s.labels["state"]: s.value for s in metrics["boinc_tasks_total"].samples}
        assert states["executing"] == 1

    def test_multiple_states_aggregated(self):
        tasks = [
            Task("t1", "http://x.org/", "files_downloaded", "executing", 0.5),
            Task("t2", "http://x.org/", "files_downloaded", "executing", 0.8),
            Task("t3", "http://x.org/", "files_uploaded", None, 0.0),
        ]
        metrics = self._run(tasks)
        states = {s.labels["state"]: s.value for s in metrics["boinc_tasks_total"].samples}
        assert states["executing"] == 2
        assert states["files_uploaded"] == 1

    def test_task_without_active_state_uses_result_state(self):
        tasks = [Task("t1", "http://x.org/", "compute_error", None, 0.0)]
        metrics = self._run(tasks)
        states = {s.labels["state"]: s.value for s in metrics["boinc_tasks_total"].samples}
        assert states["compute_error"] == 1

    def test_suspended_task_uses_active_task_state(self):
        tasks = [Task("t1", "http://x.org/", "files_downloaded", "suspended", 0.4)]
        metrics = self._run(tasks)
        states = {s.labels["state"]: s.value for s in metrics["boinc_tasks_total"].samples}
        assert "suspended" in states

    def test_empty_tasks_yields_empty_total(self):
        metrics = self._run([])
        assert metrics["boinc_tasks_total"].samples == []

    def test_fraction_done_for_executing_task(self):
        tasks = [Task("task_a", "http://x.org/", "files_downloaded", "executing", 0.75)]
        metrics = self._run(tasks)
        samples = metrics["boinc_task_fraction_done"].samples
        assert len(samples) == 1
        assert samples[0].labels["name"] == "task_a"
        assert samples[0].value == pytest.approx(0.75)

    def test_suspended_task_included_in_fraction(self):
        tasks = [Task("t1", "http://x.org/", "files_downloaded", "suspended", 0.3)]
        metrics = self._run(tasks)
        assert len(metrics["boinc_task_fraction_done"].samples) == 1
        assert metrics["boinc_task_fraction_done"].samples[0].value == pytest.approx(0.3)

    def test_task_without_active_state_excluded_from_fraction(self):
        tasks = [Task("t1", "http://x.org/", "files_uploaded", None, 0.0)]
        metrics = self._run(tasks)
        assert metrics["boinc_task_fraction_done"].samples == []


class TestProjectMetrics:
    def _run(self, projects: list) -> dict:
        with patch("boinc_exporter.collector.BOINCClient") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.get_tasks.return_value = []
            ctx.get_projects.return_value = projects
            return _collect(_make_collector())

    def test_total_credit(self):
        projects = [Project("WCG", "https://wcg.org/", 5000.0, 50.0, 200, 5)]
        metrics = self._run(projects)
        by_project = {s.labels["project"]: s.value for s in metrics["boinc_project_total_credit"].samples}
        assert by_project["WCG"] == pytest.approx(5000.0)

    def test_avg_credit(self):
        projects = [Project("WCG", "https://wcg.org/", 5000.0, 50.0, 200, 5)]
        metrics = self._run(projects)
        by_project = {s.labels["project"]: s.value for s in metrics["boinc_project_avg_credit"].samples}
        assert by_project["WCG"] == pytest.approx(50.0)

    def test_job_counts(self):
        projects = [Project("SETI", "https://seti.org/", 1000.0, 10.0, 100, 2)]
        metrics = self._run(projects)
        success = {s.labels["project"]: s.value for s in metrics["boinc_project_jobs_success_total"].samples}
        error = {s.labels["project"]: s.value for s in metrics["boinc_project_jobs_error_total"].samples}
        assert success["SETI"] == 100.0
        assert error["SETI"] == 2.0

    def test_multiple_projects(self):
        projects = [
            Project("P1", "http://p1.org/", 100.0, 10.0, 50, 0),
            Project("P2", "http://p2.org/", 200.0, 20.0, 80, 1),
        ]
        metrics = self._run(projects)
        by_project = {s.labels["project"]: s.value for s in metrics["boinc_project_total_credit"].samples}
        assert len(by_project) == 2
        assert by_project["P1"] == pytest.approx(100.0)
        assert by_project["P2"] == pytest.approx(200.0)

    def test_empty_projects(self):
        metrics = self._run([])
        for key in ("boinc_project_total_credit", "boinc_project_avg_credit",
                    "boinc_project_jobs_success_total", "boinc_project_jobs_error_total"):
            assert metrics[key].samples == []
