import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from veys.__main__ import main
from veys.hermes import register
from veys.provider import NoRedirect, complete
from veys.providers import PROVIDERS, Settings, settings
from veys.teams import plan_schema

BRIEF = "Draft a bookstore proposal."
PLAN = {"assignments": [{"role": "scope", "task": "Draft scope.", "evidence": BRIEF}]}


def reply(turns):
    system = turns[0]["content"]
    if "manager agent" in system:
        return json.dumps(PLAN)
    if "editor agent" in system:
        context = json.loads(turns[1]["content"])["earlier_drafts"]
        assert "scope" in context["work"] and context["review"]
        return "Final bookstore proposal"
    return "Draft for review"


class Integrations(unittest.TestCase):
    def test_provider_credential_boundaries(self):
        for name, spec in PROVIDERS.items():
            with self.subTest(provider=name), patch.dict(os.environ, {
                    "VEYS_PROVIDER": name, "VEYS_MODEL": "model", "VEYS_API_KEY": "private-custom"}, clear=True):
                if spec.key_env:
                    with self.assertRaisesRegex(ValueError, spec.key_env):
                        settings()
                    os.environ[spec.key_env] = "private-vendor"
                    self.assertEqual(settings().key, "private-vendor")
                    os.environ["VEYS_BASE_URL"] = "https://other.example/v1"
                    with self.assertRaisesRegex(ValueError, "custom"):
                        settings()
                else:
                    self.assertEqual(settings().url, spec.url)

    def test_cloud_request_and_redirect_boundary(self):
        with patch.dict(os.environ, {"VEYS_PROVIDER": "gemini", "VEYS_MODEL": "chat",
                                     "GEMINI_API_KEY": "test-token"}, clear=True), patch("veys.provider.build_opener") as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = b'{"choices":[{"message":{"content":"hello"}}]}'
            self.assertEqual(complete([{"role": "user", "content": "hi"}], settings()), "hello")
            req = opener.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url, PROVIDERS["gemini"].url + "/chat/completions")
            self.assertEqual(req.get_header("Authorization"), "Bearer test-token")
            self.assertTrue(any(isinstance(h, NoRedirect) for h in opener.call_args.args))
            self.assertIsNone(NoRedirect().redirect_request(req, None, 307, "", {}, "https://other.example/"))

    def test_wire_and_managed_cli(self):
        captures = []

        class Endpoint(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                captures.append((self.path, dict(self.headers), data))
                if self.path.endswith("/messages"):
                    payload = {"stop_reason": "end_turn", "content": [
                        {"type": "thinking", "thinking": "skip"}, {"type": "text", "text": "native reply"}]}
                else:
                    payload = {"choices": [{"finish_reason": "stop", "message": {"content": reply(data["messages"])}}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

        with ThreadingHTTPServer(("127.0.0.1", 0), Endpoint) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            self.addCleanup(worker.join, 1)
            try:
                url = f"http://127.0.0.1:{server.server_port}/v1"
                config = Settings("anthropic", url, "model", "messages", "test-native")
                turns = [{"role": "system", "content": "system"}, {"role": "user", "content": "hello"}]
                self.assertEqual(complete(turns, config), "native reply")
                path, headers, data = captures.pop()
                self.assertEqual((path, headers["x-api-key"], data["messages"]), ("/v1/messages", "test-native", turns[1:]))
                self.assertEqual(headers["anthropic-version"], "2023-06-01")
                with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
                    "VEYS_BASE_URL": url, "VEYS_API_KEY": "test-chat", "VEYS_MODEL": "model",
                    "VEYS_PLAN_FORMAT": "schema"}, clear=True), redirect_stdout(StringIO()) as out:
                    brief = Path(temp) / "brief"
                    brief.write_text(BRIEF)
                    run = str(Path(temp) / "run")
                    self.assertEqual(main(["run", "--team", "sales", str(brief), run]), 0)
                    self.assertEqual(main(["show", run, "--final"]), 0)
                    self.assertTrue(out.getvalue().rstrip().endswith("Final bookstore proposal"))
                self.assertEqual(len(captures), 4)
                self.assertTrue(all(path == "/v1/chat/completions" and head["Authorization"] == "Bearer test-chat"
                                    for path, head, body in captures))
                self.assertIn("response_format", captures[0][2])
            finally:
                server.shutdown()

    def test_hermes_command_ownership_and_resume(self):
        calls = []
        handlers = {}

        def infer(messages, purpose, timeout):
            calls.append(purpose)
            if purpose == "veys.editor" and calls.count(purpose) == 1:
                raise RuntimeError("private diagnostic")
            return SimpleNamespace(text=reply(messages))

        def add(name, handler, **kwargs):
            handlers[name] = handler

        ctx = SimpleNamespace(register_command=add, llm=SimpleNamespace(complete=infer))
        with tempfile.TemporaryDirectory() as tmp, patch.dict("sys.modules", {
                "plugins.plugin_storage": SimpleNamespace(plugin_data_dir=lambda _: Path(tmp))}), patch.dict(os.environ, {}, clear=True):
            register(ctx)
            command = handlers["veys"]
            source = SimpleNamespace(user_id="alice", chat_id="chat")
            args = {"platform": "telegram", "source": source, "session_key": "chat"}
            first = command("sales " + BRIEF, **args)
            run_id = first.split()[1]
            self.assertNotIn("private diagnostic", first)
            self.assertIn("paused", first)
            other = SimpleNamespace(user_id="bob", chat_id="chat")
            self.assertIn("not found", command("resume " + run_id, **{**args, "source": other}))
            self.assertIn("Final bookstore proposal", command("resume " + run_id, **args))
            self.assertEqual(calls.count("veys.manager"), 1)
            self.assertIn("identify", command("sales " + BRIEF, platform="telegram"))
            self.assertIn("/veys", command("resume ../../alice", **args))

    def test_schema_limits_evidence_to_brief(self):
        brief = "Open in March.\n" + "a" * 1234
        item = plan_schema(brief, ["scope"])["properties"]["assignments"]["items"]
        self.assertEqual(item["properties"]["role"]["enum"], ["scope"])
        for quote in item["properties"]["evidence"]["enum"]:
            self.assertIn(quote, brief)
            self.assertLessEqual(len(quote), 600)
