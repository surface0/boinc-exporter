import hashlib
import socket
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

# ResultState enum from BOINC source
_RESULT_STATES: dict[int, str] = {
    0: "new",
    1: "files_downloading",
    2: "files_downloaded",
    3: "compute_error",
    4: "files_uploading",
    5: "files_uploaded",
    6: "aborted",
    7: "upload_failed",
}

# PROCESS_STATE enum from BOINC source
_ACTIVE_TASK_STATES: dict[int, str] = {
    0: "uninitialized",
    1: "executing",
    5: "abort_pending",
    8: "quit_pending",
    9: "suspended",
    10: "copy_pending",
}


@dataclass
class Task:
    name: str
    project_url: str
    state: str
    active_task_state: Optional[str]
    fraction_done: float


@dataclass
class Project:
    name: str
    url: str
    total_credit: float
    avg_credit: float
    jobs_success: int
    jobs_error: int


class BOINCClientError(Exception):
    pass


class BOINCAuthError(BOINCClientError):
    pass


class BOINCClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 31416,
        password: str = "",
        timeout: float = 10.0,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        if self.password:
            self._authenticate()

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self) -> "BOINCClient":
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _send(self, body: str) -> ET.Element:
        msg = f"<boinc_gui_rpc_request>\n{body}\n</boinc_gui_rpc_request>\n\003"
        self._sock.sendall(msg.encode())  # type: ignore[union-attr]
        return self._recv()

    def _recv(self) -> ET.Element:
        buf = b""
        while True:
            chunk = self._sock.recv(65536)  # type: ignore[union-attr]
            if not chunk:
                raise BOINCClientError("Connection closed by BOINC client")
            buf += chunk
            if b"\003" in buf:
                buf = buf[: buf.index(b"\003")]
                break
        return ET.fromstring(buf.decode())

    def _authenticate(self) -> None:
        reply = self._send("<auth1/>")
        nonce = reply.findtext("nonce")
        if nonce is None:
            raise BOINCAuthError("No nonce in auth1 reply")
        nonce_hash = hashlib.md5(f"{nonce}{self.password}".encode()).hexdigest()
        reply = self._send(f"<auth2><nonce_hash>{nonce_hash}</nonce_hash></auth2>")
        if reply.find("authorized") is None:
            raise BOINCAuthError("BOINC authentication failed: wrong password")

    def get_tasks(self) -> list[Task]:
        reply = self._send("<get_results><active_only>0</active_only></get_results>")
        tasks: list[Task] = []
        for r in reply.findall("results/result"):
            state_code = int(r.findtext("state", "0"))
            active_el = r.find("active_task")
            active_state: Optional[str] = None
            fraction = 0.0
            if active_el is not None:
                ast = int(active_el.findtext("active_task_state", "0"))
                active_state = _ACTIVE_TASK_STATES.get(ast)
                fraction = float(active_el.findtext("fraction_done", "0"))
            tasks.append(Task(
                name=r.findtext("name", ""),
                project_url=r.findtext("project_url", ""),
                state=_RESULT_STATES.get(state_code, "unknown"),
                active_task_state=active_state,
                fraction_done=fraction,
            ))
        return tasks

    def get_projects(self) -> list[Project]:
        reply = self._send("<get_project_status/>")
        projects: list[Project] = []
        for p in reply.findall("projects/project"):
            projects.append(Project(
                name=p.findtext("project_name", ""),
                url=p.findtext("master_url", ""),
                total_credit=float(p.findtext("user_total_credit", "0")),
                avg_credit=float(p.findtext("user_expavg_credit", "0")),
                jobs_success=int(p.findtext("njobs_success", "0")),
                jobs_error=int(p.findtext("njobs_error", "0")),
            ))
        return projects
