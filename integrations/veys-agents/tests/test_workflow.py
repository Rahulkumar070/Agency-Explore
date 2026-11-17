import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

from veys.__main__ import main as cli
from veys.agents import TEAM
from veys.provider import generate
from veys.workflow import connect, create, render, resume


class WorkflowTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name) / "run"

    def test_demo_cli_is_offline_and_reopens(self):
        out = io.StringIO()
        with patch("http.client.HTTPConnection.request", side_effect=AssertionError), redirect_stdout(out):
            self.assertEqual(cli(["demo", str(self.folder)]), 0)
            initial = out.getvalue()
            self.assertIn("₹45,000", initial)
            self.assertIn("Delivery handoff", initial)
            out.seek(0)
            out.truncate()
            self.assertEqual(cli(["show", str(self.folder)]), 0)
            self.assertEqual(out.getvalue(), initial)

    def test_failure_and_resume_preserve_handoffs(self):
        create(self.folder, "A new page", "live")
        calls = []

        def model(agent, brief, drafts):
            calls.append(agent.name)
            self.assertEqual(brief, "A new page")
            if len(calls) == 2:
                raise ValueError("Unavailable")
            if agent.name == "delivery":
                self.assertEqual(drafts, {"discovery": "notes", "proposal": "notes"})
            return "notes"

        with self.assertRaises(ValueError):
            resume(self.folder, model)
        self.assertIn("Pending.", render(self.folder))
        resume(self.folder, model)
        resume(self.folder, model)
        self.assertEqual(calls, ["discovery", "proposal", "proposal", "delivery"])
        self.assertNotIn("Pending.", render(self.folder))

    def test_existing_run_survives_duplicate_create(self):
        create(self.folder, "First brief", "live")
        with self.assertRaises(FileExistsError):
            create(self.folder, "Second brief", "live")
        self.assertIn("First brief", render(self.folder))

    def test_writer_contention_stops_duplicate_calls(self):
        create(self.folder, "First brief", "live")
        from sqlite3 import OperationalError
        db = connect(self.folder)
        self.addCleanup(db.close)
        db.execute("BEGIN IMMEDIATE")
        with self.assertRaises(OperationalError):
            resume(self.folder, lambda *args: self.fail("Duplicate call"))
        db.rollback()
        resume(self.folder, lambda *args: "Done")

    def test_empty_brief_creates_no_directory(self):
        with self.assertRaises(ValueError):
            create(self.folder, " ", "live")
        self.assertFalse(self.folder.exists())


class ProviderTests(TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"VEYS_MODEL": "test-model"}, clear=True)
        env.start()
        self.addCleanup(env.stop)

    @patch("veys.provider.http.client.HTTPConnection")
    def test_request_and_reply(self, connection):
        client = connection.return_value
        response = client.getresponse.return_value
        response.status = 200
        response.read.return_value = b'{"choices":[{"message":{"content":"Draft"}}]}'
        self.assertEqual(generate(TEAM[1], "Example", {"discovery": "Notes"}), "Draft")
        request = client.request.call_args
        self.assertEqual(request.args, ("POST", "/v1/chat/completions"))
        payload = json.loads(request.kwargs["body"])
        self.assertEqual(payload["model"], "test-model")
        context = json.loads(payload["messages"][1]["content"])
        self.assertEqual(context["earlier_drafts"], {"discovery": "Notes"})
        client.close.assert_called_once()

    @patch("veys.provider.http.client.HTTPConnection")
    def test_rejects_invalid_model_responses(self, connection):
        response = connection.return_value.getresponse.return_value
        for status, body in [(429, b""), (200, b"{}"), (200, b"invalid"),
                             (200, b'{"choices":[{"message":{"content":" "}}]}'),
                             (200, b'{"choices":[{"finish_reason":"length"}]}')]:
            with self.subTest(status=status, body=body):
                response.status = status
                response.read.return_value = body
                with self.assertRaises(ValueError):
                    generate(TEAM[0], "brief", {})

    def test_remote_endpoint_requires_https(self):
        with patch.dict(os.environ, {"VEYS_BASE_URL": "http://example.com/v1"}):
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                generate(TEAM[0], "brief", {})


if __name__ == "__main__":
    main()
