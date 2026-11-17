import sqlite3
from contextlib import closing
from pathlib import Path

from .agents import DEMO_DRAFTS, TEAM
from .provider import generate
from . import managed


def create(directory, brief, mode, desk=None, metrics=None):
    if not brief.strip() or len(brief) > 32_000:
        raise ValueError("Provide a brief between 1 and 32,000 characters.")
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    with closing(sqlite3.connect(directory / "run.sqlite3")) as db, db:
        db.execute("BEGIN")
        db.execute("CREATE TABLE project (brief TEXT NOT NULL, mode TEXT NOT NULL)")
        db.execute("CREATE TABLE drafts (agent TEXT PRIMARY KEY, content TEXT NOT NULL)")
        db.execute("INSERT INTO project VALUES (?, ?)", (brief, mode))
        if desk is not None:
            managed.initialize(db, desk, metrics)


def connect(directory):
    uri = (Path(directory) / "run.sqlite3").resolve().as_uri()
    return sqlite3.connect(uri + "?mode=rw", uri=True, timeout=2)


def resume(directory, generator=generate):
    with closing(connect(directory)) as db:
        brief, mode = db.execute("SELECT brief, mode FROM project").fetchone()
        if managed.is_team(db):
            return managed.run(db, directory, brief, mode, generator)
        for agent in TEAM:
            # Serialize this run's model calls. A crash releases the lock and
            # rolls back only the current agent's draft.
            with db:
                db.execute("BEGIN IMMEDIATE")
                drafts = dict(db.execute("SELECT agent, content FROM drafts"))
                if agent.name in drafts:
                    continue
                content = DEMO_DRAFTS[agent.name] if mode == "demo" else generator(agent, brief, drafts)
                db.execute("INSERT INTO drafts VALUES (?, ?)", (agent.name, content))


def render(directory, status=False, final_only=False):
    with closing(connect(directory)) as db:
        brief, mode = db.execute("SELECT brief, mode FROM project").fetchone()
        db.execute("BEGIN")
        if managed.is_team(db):
            return managed.report(db, brief, mode, status, final_only)
        drafts = dict(db.execute("SELECT agent, content FROM drafts"))
    if final_only:
        raise ValueError("The final editor output is available for managed teams")
    if status:
        return "\n".join(f"{agent.name}: {'saved' if agent.name in drafts else 'pending'}" for agent in TEAM)
    title = "Agency work pack" if mode == "live" else "Agency work pack (offline sample)"
    sections = [f"# {title}", f"## Client brief\n\n{brief}"]
    for agent in TEAM:
        sections.append(f"## {agent.title}\n\n{drafts.get(agent.name, 'Pending.')}")
    return "\n\n".join(sections)
