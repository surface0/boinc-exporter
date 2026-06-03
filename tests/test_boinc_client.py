import hashlib
from unittest.mock import MagicMock, patch

import pytest

from boinc_exporter.boinc_client import (
    BOINCAuthError,
    BOINCClient,
    BOINCClientError,
    Project,
    Task,
)


def _xml_reply(*body_parts: str) -> bytes:
    inner = "".join(body_parts)
    return f"<boinc_gui_rpc_reply>{inner}</boinc_gui_rpc_reply>\003".encode()


def _connected_client() -> tuple[BOINCClient, MagicMock]:
    """Return a connected BOINCClient (no auth) and its underlying mock socket."""
    sock = MagicMock()
    with patch("socket.create_connection", return_value=sock):
        client = BOINCClient(password="")
        client.connect()
    return client, sock


class TestConnect:
    def test_no_auth_when_password_empty(self):
        sock = MagicMock()
        with patch("socket.create_connection", return_value=sock):
            BOINCClient(password="").connect()
        sock.recv.assert_not_called()

    def test_close_calls_socket_close(self):
        sock = MagicMock()
        with patch("socket.create_connection", return_value=sock):
            client = BOINCClient(password="")
            client.connect()
            client.close()
        sock.close.assert_called_once()

    def test_close_twice_is_safe(self):
        sock = MagicMock()
        with patch("socket.create_connection", return_value=sock):
            client = BOINCClient(password="")
            client.connect()
        client.close()
        client.close()  # should not raise

    def test_context_manager_closes_socket(self):
        sock = MagicMock()
        with patch("socket.create_connection", return_value=sock):
            with BOINCClient(password=""):
                pass
        sock.close.assert_called_once()


class TestAuthentication:
    def _nonce_hash(self, nonce: str, password: str) -> str:
        return hashlib.md5(f"{nonce}{password}".encode()).hexdigest()

    def test_successful_auth(self):
        password = "s3cr3t"
        nonce = "abc123"
        expected_hash = self._nonce_hash(nonce, password)

        sock = MagicMock()
        sock.recv.side_effect = [
            _xml_reply(f"<nonce>{nonce}</nonce>"),
            _xml_reply("<authorized/>"),
        ]
        with patch("socket.create_connection", return_value=sock):
            BOINCClient(password=password).connect()

        sent = b"".join(c.args[0] for c in sock.sendall.call_args_list)
        assert expected_hash.encode() in sent

    def test_wrong_password_raises(self):
        sock = MagicMock()
        sock.recv.side_effect = [
            _xml_reply("<nonce>xyz</nonce>"),
            _xml_reply("<unauthorized/>"),
        ]
        with patch("socket.create_connection", return_value=sock):
            with pytest.raises(BOINCAuthError, match="wrong password"):
                BOINCClient(password="bad").connect()

    def test_missing_nonce_raises(self):
        sock = MagicMock()
        sock.recv.side_effect = [_xml_reply("<error>bad</error>")]
        with patch("socket.create_connection", return_value=sock):
            with pytest.raises(BOINCAuthError, match="nonce"):
                BOINCClient(password="secret").connect()


class TestGetTasks:
    def test_empty_results(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply("<results></results>")]
        assert client.get_tasks() == []

    def test_executing_task(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply(
            "<results><result>",
            "<name>task_001</name>",
            "<project_url>http://example.org/boinc/</project_url>",
            "<state>2</state>",
            "<active_task>",
            "<active_task_state>1</active_task_state>",
            "<fraction_done>0.42</fraction_done>",
            "</active_task>",
            "</result></results>",
        )]
        tasks = client.get_tasks()
        assert len(tasks) == 1
        t = tasks[0]
        assert t.name == "task_001"
        assert t.state == "files_downloaded"
        assert t.active_task_state == "executing"
        assert t.fraction_done == pytest.approx(0.42)

    def test_completed_task_has_no_active_state(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply(
            "<results><result>",
            "<name>done</name>",
            "<project_url>http://example.org/</project_url>",
            "<state>5</state>",
            "</result></results>",
        )]
        t = client.get_tasks()[0]
        assert t.state == "files_uploaded"
        assert t.active_task_state is None
        assert t.fraction_done == 0.0

    def test_suspended_task(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply(
            "<results><result>",
            "<name>paused</name>",
            "<project_url>http://example.org/</project_url>",
            "<state>2</state>",
            "<active_task>",
            "<active_task_state>9</active_task_state>",
            "<fraction_done>0.7</fraction_done>",
            "</active_task>",
            "</result></results>",
        )]
        assert client.get_tasks()[0].active_task_state == "suspended"

    def test_unknown_state_code(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply(
            "<results><result>",
            "<name>odd</name>",
            "<project_url>http://x.org/</project_url>",
            "<state>99</state>",
            "</result></results>",
        )]
        assert client.get_tasks()[0].state == "unknown"

    def test_multiple_tasks(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply(
            "<results>",
            "<result><name>t1</name><project_url>http://x.org/</project_url><state>2</state>"
            "<active_task><active_task_state>1</active_task_state>"
            "<fraction_done>0.1</fraction_done></active_task></result>",
            "<result><name>t2</name><project_url>http://x.org/</project_url><state>5</state></result>",
            "</results>",
        )]
        tasks = client.get_tasks()
        assert len(tasks) == 2
        assert tasks[0].name == "t1"
        assert tasks[1].name == "t2"


class TestGetProjects:
    def test_single_project(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply(
            "<projects><project>",
            "<project_name>World Community Grid</project_name>",
            "<master_url>https://www.worldcommunitygrid.org/</master_url>",
            "<user_total_credit>9876.5</user_total_credit>",
            "<user_expavg_credit>123.4</user_expavg_credit>",
            "<njobs_success>500</njobs_success>",
            "<njobs_error>3</njobs_error>",
            "</project></projects>",
        )]
        projects = client.get_projects()
        assert len(projects) == 1
        p = projects[0]
        assert p.name == "World Community Grid"
        assert p.url == "https://www.worldcommunitygrid.org/"
        assert p.total_credit == pytest.approx(9876.5)
        assert p.avg_credit == pytest.approx(123.4)
        assert p.jobs_success == 500
        assert p.jobs_error == 3

    def test_empty_projects(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply("<projects></projects>")]
        assert client.get_projects() == []

    def test_multiple_projects(self):
        client, sock = _connected_client()
        sock.recv.side_effect = [_xml_reply(
            "<projects>",
            "<project><project_name>P1</project_name><master_url>http://p1.org/</master_url>"
            "<user_total_credit>100</user_total_credit><user_expavg_credit>10</user_expavg_credit>"
            "<njobs_success>10</njobs_success><njobs_error>0</njobs_error></project>",
            "<project><project_name>P2</project_name><master_url>http://p2.org/</master_url>"
            "<user_total_credit>200</user_total_credit><user_expavg_credit>20</user_expavg_credit>"
            "<njobs_success>20</njobs_success><njobs_error>1</njobs_error></project>",
            "</projects>",
        )]
        projects = client.get_projects()
        assert len(projects) == 2
        assert projects[0].name == "P1"
        assert projects[1].name == "P2"


class TestRecvMultipleChunks:
    def test_response_split_across_recv_calls(self):
        client, sock = _connected_client()
        part1 = b"<boinc_gui_rpc_reply><results></results>"
        part2 = b"</boinc_gui_rpc_reply>\003"
        sock.recv.side_effect = [part1, part2]
        assert client.get_tasks() == []

    def test_connection_closed_raises(self):
        client, sock = _connected_client()
        sock.recv.return_value = b""
        with pytest.raises(BOINCClientError, match="closed"):
            client.get_tasks()
