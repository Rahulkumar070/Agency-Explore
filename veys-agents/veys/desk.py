"""Agency commands shared by the terminal desk and scripts."""
import argparse
import json
import os
import shlex
import sys
import tempfile
from contextlib import closing, contextmanager
from functools import partial
from pathlib import Path

from . import projects
from .local import default_model, local_model
from .provider import generate
from .providers import PROVIDERS, settings, endpoint
from .team_sample import BRIEF
from .teams import DESKS
from .workflow import connect, render

ACTIONS = ("board", "new", "example", "setup", "work", "review", "revise", "approve",
           "export", "history", "tasks", "add-task", "done", "progress", "handoff", "accept", "intake")
PROJECT_ACTIONS = ACTIONS[4:]


def parsers(commands):
    commands.add_parser("desk", help="Open the interactive agency desk")
    board = commands.add_parser("board", help="List client projects, stages and open tasks")
    board.add_argument("--client")
    new = commands.add_parser("new", help="Create a project from a client brief")
    new.add_argument("--client", required=True)
    new.add_argument("--title", required=True)
    new.add_argument("--team", choices=DESKS, default="agency")
    inputs = new.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--brief", type=Path, help="Text or Markdown file")
    inputs.add_argument("--text", help="Brief text")
    commands.add_parser("example", help="Create and run the fictional offline agency project")
    setup = commands.add_parser("setup", help="Save the project workspace model selection")
    models = setup.add_mutually_exclusive_group(required=True)
    models.add_argument("--local", type=Path, metavar="GGUF")
    models.add_argument("--provider", choices=PROVIDERS)
    setup.add_argument("--model")
    setup.add_argument("--url", help="Custom Chat Completions base URL")
    helps = ("Run or resume the specialist team", "Read an editor or operator draft",
             "Save a corrected draft from a file", "Approve a specific draft version",
             "Write the approved delivery file", "List draft versions and change notes",
             "List project tasks", "Assign a project task", "Mark a task done", "Inspect team checkpoints",
             "Give an approved draft and assignment to another team",
             "Record client acceptance of a specific version", "Read the project or kickoff brief")
    for action, description in zip(PROJECT_ACTIONS, helps, strict=True):
        p = commands.add_parser(action, help=description)
        p.add_argument("id", help="Project ID from the board")
        if action == "work":
            p.add_argument("--ask-key", action="store_true")
        if action == "review":
            p.add_argument("--version", type=int)
            p.add_argument("--draft-only", action="store_true", help="Print only the editable deliverable")
        if action in {"revise", "approve", "handoff", "accept"}:
            p.add_argument("--version", type=int, required=True)
        if action == "revise":
            p.add_argument("--file", type=Path, required=True)
            p.add_argument("--note", required=True)
        if action == "accept":
            p.add_argument("--by", required=True, help="Client contact who accepted")
            p.add_argument("--evidence", required=True, help="Reference to the received confirmation")
        if action == "handoff":
            p.add_argument("--owner", help="Person or role receiving this assignment")
            p.add_argument("--open-items", help="Decisions still outstanding at handoff")
            p.add_argument("--team", required=True, choices=DESKS)
            p.add_argument("--assignment", required=True)
            p.add_argument("--excerpt", type=Path, help="File containing an exact excerpt of the approved draft")
        if action == "add-task":
            p.add_argument("title")
            p.add_argument("--owner", default="Me")
        if action == "done":
            p.add_argument("task_id", type=int)


def setup(args):
    if args.local:
        if args.model or args.url:
            raise ValueError("Use --local with the GGUF file alone.")
        model = args.local.expanduser().resolve()
        if not model.is_file():
            raise ValueError("Local model file does not exist.")
        profile = {"local": str(model)}
    else:
        if not args.model or not args.model.strip():
            raise ValueError("Supply --model with the provider's model ID.")
        url = endpoint(args.provider, args.url or "")
        profile = {"provider": args.provider, "model": args.model.strip(), "url": url}
    root = projects.home()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=root, mode="w", delete=False) as out:
        json.dump(profile, out)
    os.replace(out.name, root / "model.json")
    print(f"Saved model selection in {root}.")


@contextmanager
def model_for_work(ask_key):
    config = projects.home() / "model.json"
    profile = json.loads(config.read_text("utf-8")) if config.exists() else {}
    if profile.get("local") or (not profile and not os.getenv("VEYS_MODEL") and default_model().is_file()):
        if ask_key:
            raise ValueError("The selected local model runs without an API key.")
        with local_model(Path(profile.get("local") or default_model())) as model:
            yield model
        return
    cfg = settings(ask_key, selection=profile or None)
    yield partial(generate, config=cfg)


def dispatch(args):
    action = args.command
    if action == "board":
        rows = projects.board(args.client)
        if not rows:
            print("No matching projects. Start one with 'new' or try 'example'.")
        for _, pid, client, title, team, stage, tasks in rows:
            print(f"{pid}  {client} / {title}  [{team}]  {stage}  ·  {tasks} open tasks")
    elif action == "setup":
        setup(args)
    elif action in {"new", "example"}:
        if action == "example":
            pid = projects.new("Sample client", "Coffee campaign (offline example)", BRIEF, "agency", "demo")
            projects.work(projects.folder(pid), generate)
        else:
            brief = args.brief.read_text("utf-8") if args.brief else args.text
            pid = projects.new(args.client, args.title, brief, args.team)
        print(pid)
        return pid
    else:
        path = projects.folder(args.id)
        if action == "work":
            with closing(connect(path)) as db:
                ready = db.execute("SELECT 1 FROM steps WHERE id='editor'").fetchone()
                demo = db.execute("SELECT mode FROM project").fetchone()[0] == "demo"
            if ready or demo:
                projects.work(path, generate)
            else:
                print(f"Working on {args.id}. See checkpoints with 'veys progress {args.id}'.", flush=True)
                with model_for_work(args.ask_key) as generator:
                    projects.work(path, generator)
            print(f"Ready for review. Use 'veys review {args.id}'.")
        elif action == "handoff":
            excerpt = args.excerpt.read_text("utf-8") if args.excerpt else None
            pid = projects.handoff(path, args.version, args.team, args.assignment, excerpt,
                                   owner=args.owner, open_items=args.open_items)
            print(pid)
            return pid
        elif action == "review":
            print(projects.review(path, args.version, args.draft_only))
        elif action == "intake":
            print(projects.intake(path))
        elif action == "accept":
            projects.accept(path, args.version, args.by, args.evidence)
            print(f"Recorded client acceptance of v{args.version}.")
        elif action == "progress":
            print(render(path, status=True))
        elif action == "revise":
            version = projects.revise(path, args.file.read_text("utf-8"), args.note, args.version)
            print(f"Saved draft v{version} for review.")
        elif action == "approve":
            projects.approve(path, args.version)
            print(f"Approved v{args.version}.")
        elif action == "export":
            print(projects.export(path))
        elif action == "history":
            for n, note, approved, exported in projects.history(path):
                print(f"v{n}  {note}  ·  {'exported' if exported else 'approved' if approved else 'in review'}")
        elif action == "tasks":
            tasks = projects.list_tasks(path)
            for n, title, owner, done in tasks:
                print(f"{n}  [{'x' if done else ' '}]  {title}  ({owner})")
            if not tasks:
                print("No tasks yet.")
        elif action == "add-task":
            print(f"Added task {projects.add_task(path, args.title, args.owner)}.")
        elif action == "done":
            projects.finish_task(path, args.task_id)
            print(f"Completed task {args.task_id}.")


GUIDE = """new       Start a client project with a guided brief
example   Try the complete workflow offline
board     List projects      open ID    Select a project
work      Run the team       progress   See its checkpoints
review    Read the draft     history    See version notes
revise    Save an edit       approve    Approve a version
accept    Record client confirmation    intake    Read the kickoff brief
handoff   Brief another team from an approved version
export    Write delivery     tasks      See assigned work
add-task  Assign work        done N     Complete a task
setup     Select a model     quit       Close the desk"""


def guided(action):
    if action == "new":
        client, title = input("Client: "), input("Project name: ")
        team = input("Team (agency/sales/studio/delivery/operations) [agency]: ").strip() or "agency"
        print("Enter the brief. Finish with a line containing only a period.")
        lines = []
        while (line := input()) != ".":
            lines.append(line)
        return ["--client", client, "--title", title, "--team", team, "--text", "\n".join(lines)]
    if action == "setup":
        provider = input("Provider (or local for a GGUF file): ").strip()
        if provider == "local":
            return ["--local", input("GGUF path: ").strip()]
        args = ["--provider", provider, "--model", input("Model ID: ").strip()]
        if provider == "custom":
            args.extend(["--url", input("API base URL: ").strip()])
        return args
    if action == "revise":
        return ["--version", input("Version you edited: "), "--file", input("Edited Markdown file: "),
                "--note", input("What changed? ")]
    if action == "accept":
        return ["--version", input("Accepted version: "), "--by", input("Client contact: "),
                "--evidence", input("Confirmation reference: ")]
    if action == "handoff":
        args = ["--version", input("Approved version: "), "--team", input("Receiving team: "),
                "--assignment", input("Next assignment: ")]
        for flag, prompt in (("--owner", "Next owner [receiving team]: "), ("--open-items", "Open decisions [from brief]: ")):
            if value := input(prompt).strip():
                args.extend([flag, value])
        return args
    if action == "approve":
        return ["--version", input("Version to approve: ")]
    if action == "add-task":
        return [input("Task: "), "--owner", input("Owner [Me]: ").strip() or "Me"]
    return []


def console(parser, errors):
    selected = None
    print(f"Veys Agency Desk  |  {projects.home()}\n\n{GUIDE}")
    while True:
        try:
            line = input(f"veys{(' ' + selected) if selected else ''}> ").strip()
            if not line:
                continue
            parts = shlex.split(line)
            action, rest = parts[0], parts[1:]
            if action in {"quit", "exit"}:
                return 0
            if action == "help":
                print(GUIDE)
                continue
            if action == "open":
                if len(rest) != 1:
                    raise ValueError("Enter open followed by a project ID.")
                projects.folder(rest[0])
                selected = rest[0]
                continue
            if action not in ACTIONS:
                raise ValueError("Type help for desk commands.")
            if action in PROJECT_ACTIONS and not selected:
                raise ValueError("Open a project first, or use new or example.")
            args = rest or guided(action)
            if action in PROJECT_ACTIONS:
                args = [selected, *args]
            pid = dispatch(parser.parse_args([action, *args]))
            if pid:
                selected = pid
                print("Project selected. Type work or review to continue.")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nInterrupted. Saved checkpoints are available with progress.")
        except SystemExit:
            continue
        except errors as exc:
            print(f"Error: {exc}", file=sys.stderr)
