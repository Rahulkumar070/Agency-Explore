import argparse
import http.client
import sqlite3
import sys
from pathlib import Path

from . import desk
from .agents import SAMPLE
from .team_sample import BRIEF
from .exchange import WaitingForReplies
from functools import partial
from .provider import complete, generate
from .providers import PROVIDERS, settings
from .metrics import checkout_metrics
from .teams import DESKS, roster
from .workflow import create, render, resume


def main(argv=None):
    parser = argparse.ArgumentParser(prog="veys", description="Run your agency from client brief to reviewed delivery.")
    parser.add_argument("--version", action="version", version="Veys Agents 0.5.0")
    commands = parser.add_subparsers(dest="command", required=True)
    desk.parsers(commands)
    commands.add_parser("providers", help="List model providers and credential variables")
    doctor = commands.add_parser("doctor", help="Check the active provider configuration")
    doctor.add_argument("--live", action="store_true", help="Send one short model request")
    doctor.add_argument("--ask-key", action="store_true", help="Read a key privately for this invocation")
    catalog = commands.add_parser("catalog", help="List specialist roles and assignments")
    catalog.add_argument("--team", choices=DESKS, default="agency")
    for name, help_text in (
        ("demo", "Try the fictional offline sample"),
        ("run", "Send a brief to your configured model"),
        ("resume", "Complete unfinished drafts"),
        ("status", "Inspect saved steps"),
        ("show", "Print saved drafts as Markdown"),
    ):
        command = commands.add_parser(name, help=help_text)
        if name in {"demo", "run"}:
            command.add_argument("--team", choices=DESKS, help="Delegate to a managed specialist team")
        if name in {"run", "resume"}:
            command.add_argument("--ask-key", action="store_true", help="Read a key privately for this invocation")
        if name == "show":
            command.add_argument("--final", action="store_true", help="Print only the managed editor output")
        if name == "run":
            command.add_argument("--via-files", action="store_true", help="Exchange prompts and responses through local files")
            command.add_argument("--metrics", type=Path, help="Aggregate funnel CSV for a managed team")
            command.add_argument("brief", type=Path, help="UTF-8 text or Markdown file")
        command.add_argument("directory", type=Path, help="Run folder (new for demo and run)")
    argv = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(argv or (["desk"] if sys.stdin.isatty() else ["--help"]))
    errors = (OSError, ValueError, sqlite3.Error, http.client.HTTPException)
    try:
        if args.command == "desk":
            return desk.console(parser, errors)
        if args.command in desk.ACTIONS:
            desk.dispatch(args)
            return 0
        if args.command == "providers":
            for name, provider in PROVIDERS.items():
                print(f"{name:12} {provider.key_env or 'VEYS_API_KEY (optional)':25} {provider.url}")
            return 0
        if args.command == "doctor":
            config = settings(args.ask_key)
            print(f"{config.name} | {config.model} | {config.url} | settings valid")
            if args.live:
                complete([{"role": "system", "content": "Answer briefly."},
                          {"role": "user", "content": "Reply with OK."}], config)
                print("Model returned text.")
            return 0
        if args.command == "catalog":
            for role in roster(args.team).values():
                print(f"{role['desk']}/{role['name']} — {role['title']}\n  {role['instructions']}"
                      f"\n  Deliverable: {role['output']}\n  Review: {role['check']}")
            return 0
        generator = generate
        if getattr(args, "ask_key", False):
            if getattr(args, "via_files", False):
                parser.error("--ask-key is for direct model calls")
            generator = partial(generate, config=settings(ask_key=True))
        if args.command in {"demo", "run"}:
            if args.command == "demo":
                brief = BRIEF if args.team else SAMPLE
            else:
                brief = args.brief.read_text(encoding="utf-8")
            metrics = None
            if args.command == "run" and args.metrics:
                if not args.team:
                    parser.error("--metrics requires --team")
                metrics = checkout_metrics(args.metrics)
            mode = "demo" if args.command == "demo" else "live"
            if getattr(args, "via_files", False):
                if not args.team:
                    parser.error("--via-files requires --team")
                mode = "files"
            create(args.directory, brief, mode, args.team, metrics)
        if args.command not in {"show", "status"}:
            resume(args.directory, generator)
        print(render(args.directory, status=args.command == "status", final_only=getattr(args, "final", False)))
    except WaitingForReplies as exc:
        print(f"{exc}\nThen run: python3 -m veys resume {args.directory}", file=sys.stderr)
        return 0
    except FileExistsError:
        parser.exit(1, "Run folder already exists. Choose a new folder or use resume.\n")
    except errors as exc:
        hint = " Use resume with the same folder to retry." if getattr(args, "directory", None) and (args.directory / "run.sqlite3").is_file() else ""
        print(f"Error: {exc}.{hint}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
