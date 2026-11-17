"""Client projects, draft versions, delivery records and agency tasks."""
import hashlib
import json
import os
import re
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

from .scope import scope_notes
from .workflow import connect, create, resume


def home():
    return Path(os.getenv("VEYS_HOME") or ".veys").expanduser().resolve()


def folder(project_id):
    if not re.fullmatch(r"[a-f0-9]{12}", project_id):
        raise ValueError("Use the project ID shown by 'veys board'.")
    path = home() / "projects" / project_id
    if not (path / "run.sqlite3").is_file():
        raise ValueError("Project not found in this workspace.")
    return path


def clean(value, label, limit=200):
    value = value.strip()
    if not value or len(value) > limit:
        raise ValueError(f"{label} must contain 1 to {limit} characters.")
    return value


def new(client, title, brief, team, mode="live", *, project_id=None, origin=None):
    client, title = clean(client, "Client"), clean(title, "Project title")
    root = home() / "projects"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    project_id = project_id or uuid4().hex[:12]
    with tempfile.TemporaryDirectory(dir=root, prefix=".creating-") as temp:
        path = Path(temp) / "project"
        create(path, brief, mode, team)
        with closing(connect(path)) as db, db:
            db.execute("CREATE TABLE account(client TEXT, title TEXT, team TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)")
            db.execute("INSERT INTO account(client,title,team) VALUES (?,?,?)", (client, title, team))
            db.execute("""CREATE TABLE versions(number INTEGER PRIMARY KEY, body TEXT NOT NULL,
                       note TEXT NOT NULL, approved INTEGER DEFAULT 0, exported INTEGER DEFAULT 0)""")
            db.execute("""CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                       owner TEXT NOT NULL, done INTEGER DEFAULT 0)""")
            if origin:
                db.execute("CREATE TABLE origin(parent TEXT, version INTEGER, assignment TEXT, client_brief TEXT)")
                db.execute("INSERT INTO origin VALUES (?,?,?,?)", origin)
        path.rename(root / project_id)
    return project_id


@contextmanager
def transaction(path):
    with closing(connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        yield db


def work(path, generator):
    resume(path, generator)
    with transaction(path) as db:
        db.execute("""INSERT OR IGNORE INTO versions(number,body,note)
                   SELECT 1,body,'Team draft' FROM steps WHERE id='editor'""")


def latest(db):
    row = db.execute("SELECT number,body,approved,exported FROM versions ORDER BY number DESC LIMIT 1").fetchone()
    if row is None:
        raise ValueError("Run the project team first.")
    return row


def board(client=None):
    rows = []
    for path in sorted((home() / "projects").glob("*")):
        if not re.fullmatch(r"[a-f0-9]{12}", path.name):
            continue
        with closing(connect(path)) as db:
            db.execute("BEGIN")
            name, title, team, created = db.execute("SELECT * FROM account").fetchone()
            if client and client.casefold() != name.casefold():
                continue
            ver = db.execute("SELECT number,approved,exported FROM versions ORDER BY number DESC LIMIT 1").fetchone()
            if ver:
                number, approved, exported = ver
                stage = "Exported" if exported else "Approved" if approved else "In review"
                stage += f" v{number}"
                if acceptance(db, number):
                    stage += " · Client accepted"
            else:
                stage = "In progress" if db.execute("SELECT 1 FROM steps LIMIT 1").fetchone() else "Briefed"
            tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE done=0").fetchone()[0]
            rows.append((created, path.name, name, title, team, stage, tasks))
    return sorted(rows, reverse=True)


def original_brief(db):
    origin = db.execute("SELECT 1 FROM sqlite_master WHERE name='origin'").fetchone()
    query = "SELECT client_brief FROM origin" if origin else "SELECT brief FROM project"
    return db.execute(query).fetchone()[0]


def acceptance(db, version):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='client_acceptance'").fetchone():
        return None
    return db.execute("SELECT contact,evidence FROM client_acceptance WHERE version=?", (version,)).fetchone()


def acceptance_text(record):
    return f"Recorded from {record[0]} — {record[1]}" if record else "Awaiting client confirmation"


def review(path, version=None, draft_only=False):
    with closing(connect(path)) as db:
        db.execute("BEGIN")
        if version is None:
            number, body, approved, _ = latest(db)
        else:
            row = db.execute("SELECT number,body,approved FROM versions WHERE number=?", (version,)).fetchone()
            if not row:
                raise ValueError("No such draft version.")
            number, body, approved = row
        if draft_only:
            return body
        brief = original_brief(db)
        sections, warnings = scope_notes(brief, body)
        status = "Approved" if approved else "In review"
        client = acceptance_text(acceptance(db, number))
        lines = [f"Draft v{number} | Internal: {status} | Client: {client}",
                 "## Original client brief", brief, "## Scope review", *sections]
        if warnings:
            lines.extend(["## Potential scope changes", *warnings])
        lines.extend(["## Proposed deliverable", body])
        return "\n\n".join(lines)


def accept(path, version, contact, evidence):
    record = (clean(contact, "Client contact"), clean(evidence, "Acceptance evidence", 2000))
    with transaction(path) as db:
        number, _, approved, _ = latest(db)
        if number != version or not approved:
            raise ValueError("Record client acceptance for the current internally approved version.")
        db.execute("""CREATE TABLE IF NOT EXISTS client_acceptance (
                   version INTEGER PRIMARY KEY, contact TEXT, evidence TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)""")
        existing = acceptance(db, version)
        if existing and existing != record:
            raise ValueError("This version already has a different client acceptance record.")
        db.execute("INSERT OR IGNORE INTO client_acceptance(version,contact,evidence) VALUES (?,?,?)",
                   (version, *record))


def intake(path):
    with closing(connect(path)) as db:
        return db.execute("SELECT brief FROM project").fetchone()[0]


def revise(path, body, note, previous):
    body, note = clean(body, "Draft", 100_000), clean(note, "Change note", 2000)
    with transaction(path) as db:
        number, old_body, _, _ = latest(db)
        if previous != number:
            raise ValueError(f"The current draft is v{number}. Review it before changing it.")
        if old_body == body:
            raise ValueError("The edited text matches the current draft.")
        db.execute("INSERT INTO versions(number,body,note) VALUES (?,?,?)", (number + 1, body, note))
    return number + 1


def approve(path, version):
    with transaction(path) as db:
        number, _, _, _ = latest(db)
        if number != version:
            raise ValueError(f"The current draft is v{number}. Review it before approving.")
        db.execute("UPDATE versions SET approved=1 WHERE number=?", (number,))


def export(path):
    with transaction(path) as db:
        number, body, approved, _ = latest(db)
        if not approved:
            raise ValueError(f"Review and approve v{number} before exporting it.")
        target = path / "delivery" / f"work-pack-v{number}.md"
        target.parent.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, mode="w", encoding="utf-8", delete=False) as out:
            pending = Path(out.name)
            try:
                out.write(body + "\n")
                out.flush()
                os.fsync(out.fileno())
                out.close()
                os.replace(pending, target)
            finally:
                pending.unlink(missing_ok=True)
        db.execute("UPDATE versions SET exported=1 WHERE number=?", (number,))
    return target


def handoff(path, version, team, assignment, excerpt=None, *, owner=None, open_items=None):
    assignment = clean(assignment, "Next assignment", 2000)
    owner = clean(owner, "Next owner") if owner else None
    open_items = clean(open_items, "Open decisions", 2000) if open_items else None
    with transaction(path) as db:
        number, body, approved, _ = latest(db)
        if version != number or not approved:
            raise ValueError("Choose the current approved version for a handoff.")
        if excerpt is not None:
            excerpt = excerpt.strip()
            if not excerpt or excerpt not in body:
                raise ValueError("The excerpt must be a contiguous passage of the approved draft.")
            body = excerpt
        client, title = db.execute("SELECT client,title FROM account").fetchone()
        client_brief = original_brief(db)
        origin = (path.name, version, assignment, client_brief)
        identity = [path.name, version, team, assignment, body]
        if owner or open_items:
            identity.extend([owner, open_items])
        key = json.dumps(identity).encode()
        child_id = hashlib.sha256(key).hexdigest()[:12]
        child = path.parent / child_id
        if child.exists():
            with closing(connect(child)) as other:
                if other.execute("SELECT * FROM origin").fetchone() != origin:
                    raise ValueError("Project ID collision.")
            return child_id
        client_status = acceptance_text(acceptance(db, version))
        brief = (f"Current agency assignment: {assignment}\nNext owner: {owner or team}\n"
                 f"Open decisions: {open_items or 'Confirm unresolved commercial terms, dates and client inputs against the brief.'}"
                 f"\nSource project: {path.name}, draft v{version} (internally approved)."
                 f"\nClient acceptance at handoff: {client_status}\n\nOriginal client brief:\n{client_brief}"
                 f"\n\nApproved reference for this assignment:\n{body}")
        if len(brief) > 32000:
            raise ValueError("Handoff exceeds the brief limit. Supply --excerpt with a shorter passage.")
        return new(client, f"{title[:170]} / {team}", brief, team, project_id=child_id, origin=origin)


def add_task(path, title, owner):
    with transaction(path) as db:
        return db.execute("INSERT INTO tasks(title,owner) VALUES (?,?)",
                          (clean(title, "Task", 1000), clean(owner, "Owner"))).lastrowid


def finish_task(path, task_id):
    with transaction(path) as db:
        if not db.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,)).rowcount:
            raise ValueError("No such task in this project.")


def list_tasks(path):
    with closing(connect(path)) as db:
        return db.execute("SELECT id,title,owner,done FROM tasks ORDER BY done,id").fetchall()


def history(path):
    with closing(connect(path)) as db:
        return db.execute("SELECT number,note,approved,exported FROM versions ORDER BY number").fetchall()
