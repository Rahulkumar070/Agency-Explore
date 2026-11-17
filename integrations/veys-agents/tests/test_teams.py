import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from veys.exchange import WaitingForReplies
from veys.metrics import checkout_metrics
from veys.team_sample import BRIEF, sample_response
from veys.teams import DESKS, read_plan, roster
from veys.workflow import connect, create, render, resume


class TeamTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.run = self.root / "run"

    def test_all_offline_desks(self):
        with patch("http.client.HTTPConnection.request", side_effect=AssertionError):
            for desk in DESKS:
                path = self.root / desk
                create(path, BRIEF, "demo", desk)
                resume(path)
                self.assertIn("Next decision", render(path))
                self.assertNotIn("pending", render(path, status=True))
                self.assertEqual(len(roster(desk)), 12 if desk == "agency" else 3)

    def test_plan_rejects_unlisted_duplicate_excess_and_ungrounded_tasks(self):
        item = {"role": "scope", "task": "Prepare scope.", "evidence": "spending ceiling"}
        roles = roster("sales")
        for items in [[], [item] * 2, [item] * 5, [{**item, "role": "web"}],
                      [{**item, "evidence": "unmentioned"}], [{"role": "scope"}]]:
            with self.subTest(items=items), self.assertRaises(ValueError):
                read_plan(json.dumps({"assignments": items}), roles, BRIEF)

    def test_parallel_isolation_recovery_and_model_context(self):
        metrics = {"October": {"visitors": 240, "checkout_starts": 12, "checkout_start_percent": "5.00"}}
        create(self.run, BRIEF, "live", "agency", metrics)
        barrier = threading.Barrier(2)
        calls = []
        first = True

        def model(agent, brief, ctx):
            calls.append(agent.name)
            if agent.name in ("scope", "copy") and first:
                barrier.wait(timeout=3)
            if agent.name == "copy" and first:
                raise ValueError("temporary failure")
            if agent.name in ("scope", "copy", "production", "measurement"):
                self.assertEqual(ctx["assignment"]["role"], agent.name)
                self.assertNotIn("work", ctx)
                self.assertEqual("verified_checkout_metrics" in ctx, agent.name == "measurement")
            if agent.name == "editor":
                self.assertIn("review", ctx)
                self.assertEqual(ctx["verified_checkout_metrics"], metrics)
                self.assertEqual(list(ctx["work"]), ["scope", "copy", "production", "measurement"])
            return sample_response(agent, brief, ctx)

        with self.assertRaisesRegex(ValueError, "temporary failure"):
            resume(self.run, model)
        self.assertNotIn("reviewer", calls)
        state = render(self.run, status=True)
        self.assertIn("scope | saved", state)
        self.assertIn("copy | pending", state)
        first = False
        resume(self.run, model)
        resume(self.run, lambda *args: self.fail("unnecessary model call"))
        self.assertEqual(calls.count("copy"), 2)
        self.assertEqual(calls.count("manager"), 1)
        self.assertEqual(calls.count("scope"), 1)

    def test_lock_prevents_second_scheduler(self):
        create(self.run, BRIEF, "live", "agency")
        with closing(sqlite3.connect(self.run / "scheduler.sqlite3")) as lock:
            lock.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                resume(self.run, lambda *args: self.fail("Unclaimed model call"))

    def test_invalid_plan_never_dispatches(self):
        create(self.run, BRIEF, "live", "sales")
        calls = []
        def bad(agent, *args):
            calls.append(agent.name)
            return '{"assignments":[]}'
        with self.assertRaises(ValueError):
            resume(self.run, bad)
        self.assertEqual(calls, ["manager", "manager"])
        with closing(connect(self.run)) as db:
            self.assertEqual(db.execute("select count(*) from steps").fetchone()[0], 0)

    def test_file_handoffs_use_actual_messages_and_validate_replies(self):
        create(self.run, BRIEF, "files", "operations")
        responses = self.run / "responses"
        requests = self.run / "requests"
        with self.assertRaises(WaitingForReplies):
            resume(self.run)
        prompt = json.loads((requests / "manager.json").read_text())
        self.assertEqual(prompt[0]["role"], "system")
        inputs = json.loads(prompt[1]["content"])
        self.assertEqual(inputs["client_brief"], BRIEF)
        (responses / "manager.txt").write_text("invalid")
        with self.assertRaises(ValueError):
            resume(self.run)
        assignment = {"role": "measurement", "task": "Calculate baseline.", "evidence": "240 visitors"}
        (responses / "manager.txt").write_text(json.dumps({"assignments": [assignment]}))
        for role, body in [("measurement", "5% baseline"), ("reviewer", "Keep the denominator."),
                           ("editor", "12 checkout starts out of 240 visitors.")]:
            with self.assertRaises(WaitingForReplies):
                resume(self.run)
            self.assertTrue((requests / f"{role}.json").exists())
            (responses / f"{role}.txt").write_text(body)
        resume(self.run)
        self.assertEqual(render(self.run, final_only=True), "12 checkout starts out of 240 visitors.")

    def test_original_database_remains_readable(self):
        self.run.mkdir()
        with closing(sqlite3.connect(self.run / "run.sqlite3")) as db, db:
            db.execute("CREATE TABLE project (brief TEXT, mode TEXT)")
            db.execute("INSERT INTO project VALUES ('Existing', 'live')")
            db.execute("CREATE TABLE drafts (agent TEXT PRIMARY KEY, content TEXT)")
            db.execute("INSERT INTO drafts VALUES ('discovery','Preserve my draft')")
        resume(self.run, lambda *args: "next")
        self.assertIn("Preserve my draft", render(self.run))

    def test_funnel_counts_and_denominators(self):
        path = self.root / "funnel.csv"
        header = "period,visitors,checkout_starts\n"
        path.write_text(header + "Oct,240,12\nNov,0,0\n", encoding="utf-8")
        data = checkout_metrics(path)
        self.assertEqual(data["Oct"]["checkout_start_percent"], "5.00")
        self.assertIsNone(data["Nov"]["checkout_start_percent"])
        for rows in ["", "Oct,1,9", "Oct,1,0\nOct,2,1", "Oct,-1,0", "Oct,one,0"]:
            path.write_text(header + rows, encoding="utf-8")
            with self.assertRaises(ValueError):
                checkout_metrics(path)
