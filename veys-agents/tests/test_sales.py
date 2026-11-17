import io
import json
import os
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from unittest.mock import patch

from veys import projects
from veys.__main__ import main
from veys.scope import scope_notes
from veys.workflow import connect, render

BOOK = ("We want a single page and a link to our existing booking form. "
        "Our team can supply the event calendar and photography. "
        "We have a budget ceiling of ₹30,000. No fees or dates are agreed yet.")


class SalesWorkflowTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        env = patch.dict(os.environ, {"VEYS_HOME": workspace.name})
        env.start()
        self.addCleanup(env.stop)

    def run_command(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(list(args)), 0)
        return output.getvalue().strip()

    def test_duplicate_plan_repaired_once_then_checkpointed(self):
        path = projects.folder(projects.new("Bookshop", "Proposal", BOOK, "sales"))
        assignment = {"role": "scope", "task": "Draft the scope", "evidence": "single page"}
        calls = []
        def generate(agent, brief, context):
            calls.append(agent.name)
            if agent.name == "manager":
                if len(calls) == 1:
                    return json.dumps({"assignments": [assignment, assignment]})
                self.assertIn("repeated", context["repair"]["validation_error"])
                return json.dumps({"assignments": [assignment]})
            return "Reviewable draft"
        projects.work(path, generate)
        projects.work(path, lambda *args: self.fail("Should use saved checkpoints"))
        self.assertEqual(calls, ["manager", "manager", "scope", "reviewer", "editor"])
        self.assertIn("repeated specialist: scope", render(path, status=True))

    def test_double_failure_preserves_first_reason_and_starts_no_workers(self):
        path = projects.folder(projects.new("Bookshop", "Proposal", BOOK, "sales"))
        names = []
        replies = iter(['{"assignments":[]}', '{"assignments":[{"role":"scope"}]}'])
        def invalid(agent, brief, context):
            names.append(agent.name)
            return next(replies)
        with self.assertRaisesRegex(ValueError, "Repair failed"):
            projects.work(path, invalid)
        self.assertEqual(names, ["manager"] * 2)
        self.assertIn("Select between", render(path, status=True))
        with closing(connect(path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM steps").fetchone()[0], 0)

    def test_provider_error_does_not_trigger_planning_retry(self):
        path = projects.folder(projects.new("Bookshop", "Proposal", BOOK, "sales"))
        def unavailable(*args):
            raise ValueError("Model endpoint returned HTTP 401")
        with self.assertRaisesRegex(ValueError, "HTTP 401"):
            projects.work(path, unavailable)
        self.assertNotIn("repair requested", render(path, status=True))

    def test_review_checks_source_and_revision(self):
        draft = "Redesign the booking form.\nOur fee: ₹30,000"
        sections, flags = scope_notes(BOOK, draft)
        self.assertIn("calendar and photography", "\n".join(sections))
        for term in ("fee agreement", "added work", "client inputs"):
            self.assertIn(term, "\n".join(flags))
        _, flags = scope_notes(BOOK, "We will link to the existing booking form. "
                              "You can supply the event calendar and photography. Budget ceiling: ₹30,000.")
        self.assertEqual(flags, [])

    def test_acceptance_and_frozen_handoff_through_cli(self):
        pid = self.run_command("example")
        path = projects.folder(pid)
        self.assertIn("Awaiting client confirmation", self.run_command("review", pid))
        with self.assertRaises(ValueError):
            projects.accept(path, 1, "Test client", "Test email")
        self.run_command("approve", pid, "--version", "1")
        args = ("handoff", pid, "--version", "1", "--team", "delivery", "--owner", "Studio lead",
                "--open-items", "Fee and dates open", "--assignment", "Prepare kickoff")
        child = self.run_command(*args)
        self.assertEqual(self.run_command(*args), child)
        snapshot = self.run_command("intake", child)
        for value in ("Studio lead", "Fee and dates open", "Awaiting client confirmation", pid, "v1"):
            self.assertIn(value, snapshot)
        for _ in range(2):
            self.run_command("accept", pid, "--version", "1", "--by", "Test contact", "--evidence", "Test email #1")
        self.assertIn("Test email #1", self.run_command("review", pid))
        self.assertEqual(self.run_command(*args), child)
        self.assertEqual(self.run_command("intake", child), snapshot)
        second = projects.handoff(path, 1, "delivery", "Prepare production schedule", owner="Producer")
        self.assertIn("Test email #1", projects.intake(projects.folder(second)))
        projects.revise(path, "Edited draft", "Scope correction", 1)
        self.assertIn("Awaiting client confirmation", projects.review(path))
        self.assertIn("Test email #1", projects.review(path, 1))
        self.assertEqual(projects.review(path, draft_only=True), "Edited draft")
        self.assertEqual(projects.intake(projects.folder(child)), snapshot)
