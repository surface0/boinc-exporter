from prometheus_client.core import GaugeMetricFamily

from .boinc_client import BOINCClient


class BOINCCollector:
    def __init__(self, host: str, port: int, password: str) -> None:
        self.host = host
        self.port = port
        self.password = password

    def collect(self):  # type: ignore[return]
        up = GaugeMetricFamily("boinc_up", "1 if the BOINC client is reachable, 0 otherwise")
        try:
            with BOINCClient(self.host, self.port, self.password) as client:
                tasks = client.get_tasks()
                projects = client.get_projects()
        except Exception:
            up.add_metric([], 0)
            yield up
            return

        up.add_metric([], 1)
        yield up

        state_counts: dict[str, int] = {}
        for task in tasks:
            state = task.active_task_state if task.active_task_state else task.state
            state_counts[state] = state_counts.get(state, 0) + 1

        g = GaugeMetricFamily(
            "boinc_tasks_total",
            "Number of BOINC tasks by state",
            labels=["state"],
        )
        for state, count in state_counts.items():
            g.add_metric([state], count)
        yield g

        prog = GaugeMetricFamily(
            "boinc_task_fraction_done",
            "Completion fraction (0–1) for tasks with an active process",
            labels=["name", "project_url"],
        )
        for task in tasks:
            if task.active_task_state is not None:
                prog.add_metric([task.name, task.project_url], task.fraction_done)
        yield prog

        total_credit = GaugeMetricFamily(
            "boinc_project_total_credit",
            "Total accumulated credit",
            labels=["project", "url"],
        )
        avg_credit = GaugeMetricFamily(
            "boinc_project_avg_credit",
            "Recent average daily credit",
            labels=["project", "url"],
        )
        jobs_success = GaugeMetricFamily(
            "boinc_project_jobs_success_total",
            "Total successfully completed jobs",
            labels=["project", "url"],
        )
        jobs_error = GaugeMetricFamily(
            "boinc_project_jobs_error_total",
            "Total failed jobs",
            labels=["project", "url"],
        )

        for proj in projects:
            labels = [proj.name, proj.url]
            total_credit.add_metric(labels, proj.total_credit)
            avg_credit.add_metric(labels, proj.avg_credit)
            jobs_success.add_metric(labels, proj.jobs_success)
            jobs_error.add_metric(labels, proj.jobs_error)

        yield total_credit
        yield avg_credit
        yield jobs_success
        yield jobs_error
