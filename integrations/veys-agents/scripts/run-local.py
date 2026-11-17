#!/usr/bin/env python3
"""Run a managed Veys workflow with a local GGUF model."""
import argparse
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from veys.local import default_model, local_model
from veys.teams import DESKS
from veys.workflow import create, render, resume


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", nargs="?", type=Path, default=ROOT / "examples/client-brief.md")
    parser.add_argument("--team", choices=DESKS, default="sales")
    parser.add_argument("--model", type=Path, default=default_model())
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output", type=Path)
    output.add_argument("--resume", type=Path)
    args = parser.parse_args()
    path = args.resume or args.output or ROOT / "runs" / f"local-{uuid4().hex[:12]}"
    print(f"Run folder: {path}", flush=True)
    try:
        with local_model(args.model) as model:
            if not args.resume:
                create(path, args.brief.read_text("utf-8"), "live", args.team)
            resume(path, model)
        print(render(path))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(run())
