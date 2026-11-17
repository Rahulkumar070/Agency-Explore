"""Bounded manager → independent specialists → review → synthesis."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
from contextvars import copy_context
from time import monotonic
from functools import partial

from .agents import Agent
from .exchange import WaitingForReplies, exchange
from .team_sample import sample_response
from .teams import EDITOR, MANAGER, REVIEWER, read_plan, roster


def initialize(db, desk, metrics=None):
    spec = {"metrics": metrics or {}, "desk": desk, "roles": roster(desk), "manager": MANAGER,
            "reviewer": REVIEWER, "editor": EDITOR}
    if desk == "sales":
        spec["editor"] += (" Produce a discovery follow-up the owner can send, a proposed scope, "
                           "and the next client decision. Quote the stated budget and asset ownership "
                           "accurately. Linking to an existing service does not include changing it.")
    db.execute("CREATE TABLE team (spec TEXT NOT NULL)")
    db.execute("INSERT INTO team VALUES (?)", (json.dumps(spec),))
    db.execute("""CREATE TABLE steps (id TEXT PRIMARY KEY, body TEXT NOT NULL,
                   elapsed_ms INTEGER NOT NULL, completed TEXT DEFAULT CURRENT_TIMESTAMP)""")


def is_team(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='team'").fetchone())


def load(db):
    spec = json.loads(db.execute("SELECT spec FROM team").fetchone()[0])
    saved = dict(db.execute("SELECT id, body FROM steps"))
    return spec, saved


def run(db, directory, brief, mode, generator):
    # A separate SQLite writer lock elects one scheduler for this run. The
    # results DB stays writable for each checkpoint and readable for status.
    with closing(sqlite3.connect(directory / "scheduler.sqlite3", timeout=2)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        spec, saved = load(db)
        model = {"demo": sample_response, "files": partial(exchange, directory)}.get(mode, generator)

        def call(agent, context):
            start = monotonic()
            body = model(agent, brief, context)
            if not isinstance(body, str) or not body.strip() or len(body) > 100_000:
                if agent.name == "manager" and mode == "live":
                    return "", round(1000 * (monotonic() - start))
                raise ValueError(f"Invalid output from {agent.name}.")
            return body.strip(), round(1000 * (monotonic() - start))

        def save(name, body, elapsed):
            with db:
                db.execute("INSERT INTO steps (id,body,elapsed_ms) VALUES (?,?,?)", (name, body, elapsed))
            saved[name] = body

        metrics = spec.get("metrics", {})
        roles = spec["roles"]
        if "manager" not in saved:
            manager = Agent("manager", "Assignments", spec["manager"], "a single JSON object")
            context = {"desk": spec["desk"], "has_funnel_metrics": bool(metrics),
                       "roster": {k: v["instructions"] for k, v in roles.items()}}
            raw, ms = call(manager, context)
            try:
                plan = read_plan(raw, roles, brief)
            except ValueError as first:
                if mode != "live":
                    raise
                with db:
                    db.execute("CREATE TABLE IF NOT EXISTS plan_repairs (reason TEXT NOT NULL, "
                               "created TEXT DEFAULT CURRENT_TIMESTAMP)")
                    db.execute("INSERT INTO plan_repairs(reason) VALUES (?)", (str(first),))
                context["repair"] = {"validation_error": str(first), "previous_output": raw[:6000]}
                repair = Agent("manager", "Repair assignments", spec["manager"] +
                               " Your last plan failed validation. Select one permitted lead specialist "
                               "and give them a task covering the requested work. Copy the evidence exactly.",
                               "a single JSON object")
                fixed, extra_ms = call(repair, context)
                try:
                    plan = read_plan(fixed, roles, brief)
                except ValueError as second:
                    raise ValueError(f"Planning failed: {first}. Repair failed: {second}. "
                                     "Check the brief or choose a different model and run again.") from second
                ms += extra_ms
            save("manager", json.dumps({"assignments": plan}, ensure_ascii=False), ms)
        else:
            plan = read_plan(saved["manager"], roles, brief)

        assignments = {item["role"]: item for item in plan}
        failures = []
        pending = []
        with ThreadPoolExecutor(max_workers=3) as workers:
            active = {}
            for name, item in assignments.items():
                if name in saved:
                    continue
                role = roles[name]
                worker = Agent(name, role["title"], role["instructions"], role.get("output", "concise Markdown"))
                inputs = {"assignment": item}
                if metrics and name in {"measurement", "accounts"}:
                    inputs["verified_checkout_metrics"] = metrics
                active[workers.submit(copy_context().run, call, worker, inputs)] = name
            for result in as_completed(active):
                name = active[result]
                try:
                    body, ms = result.result()
                except WaitingForReplies as exc:
                    pending.append(str(exc))
                    continue
                except Exception as exc:
                    # Drain every sibling before reporting failure so completed
                    # work can be retained when a different provider call fails.
                    failures.append((name, exc))
                    continue
                save(name, body, ms)
        if failures:
            name, failure = failures[0]
            raise ValueError(f"Specialist {name} failed: {failure}") from failure

        if pending:
            raise WaitingForReplies("\n".join(sorted(pending)))

        work = {name: saved[name] for name in assignments}
        shared = {"assignments": plan, "work": work}
        checks = {name: roles[name]["check"] for name in assignments if "check" in roles[name]}
        if checks:
            shared["review_criteria"] = checks
        if metrics:
            shared["verified_checkout_metrics"] = metrics
        if "reviewer" not in saved:
            save("reviewer", *call(Agent("reviewer", "Editorial review", spec["reviewer"]), shared))
        if "editor" not in saved:
            editor = Agent("editor", "Final work pack", spec["editor"])
            save("editor", *call(editor, {**shared, "review": saved["reviewer"]}))


def report(db, brief, mode, status=False, final_only=False):
    spec, saved = load(db)
    if final_only:
        if "editor" not in saved:
            raise ValueError("The final work pack is still pending")
        return saved["editor"]
    plan = read_plan(saved["manager"], spec["roles"], brief) if "manager" in saved else []
    names = [item["role"] for item in plan]
    if status:
        timings = dict(db.execute("SELECT id, elapsed_ms FROM steps"))
        lines = [f"Desk: {spec['desk']} | Mode: {mode}", "Step | Status | Duration"]
        for name in ["manager", *names, "reviewer", "editor"]:
            value = f"saved | {timings[name]} ms" if name in timings else "pending | —"
            lines.append(f"{name} | {value}")
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='plan_repairs'").fetchone():
            for (reason,) in db.execute("SELECT reason FROM plan_repairs ORDER BY rowid"):
                lines.append(f"Plan repair requested: {reason}")
        return "\n".join(lines)
    label = " (offline fixture)" if mode == "demo" else ""
    sections = [f"# {spec['desk'].title()} work pack{label}", saved.get("editor", "Final synthesis pending."),
                "## Client brief", brief, "## Delegation record"]
    for item in plan:
        name = item["role"]
        sections.extend([f"### {spec['roles'][name]['title']}", f"Assignment: {item['task']}",
                         f"Brief evidence: {item['evidence']}", saved.get(name, "Pending.")])
    sections.extend(["## Editorial review", saved.get("reviewer", "Pending.")])
    return "\n\n".join(sections)
