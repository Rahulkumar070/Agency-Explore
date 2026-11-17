"""Run reproducible agency acceptance probes, offline or against a configured model."""
import argparse
import json
import os
import re
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from veys.team_sample import BRIEF
from veys.workflow import connect, create, resume

# Score only the final deliverable. A fact echoed in the original brief or
# hidden in a scratch draft cannot earn credit for the client-facing output.
CASES = {
    "sales": {
        "budget amount": r"(?:₹|INR|Rs\.?)?\s*45,?000",
        "budget distinguished": r"ceiling|budget|upper limit|cap\b",
        "unsettled commercial term": r"(?:agree|confirm|unconfirmed|open|pending|propos|discuss).{0,65}(?:fee|pricing|quote)|(?:fee|pricing|quote).{0,65}(?:open|pending|agree|confirm|undecided)",
    },
    "studio": {
        "two social concepts": r"post (?:2|two)|second post|post #?2|two (?:instagram )?posts",
        "customer question": r"interval|how often|frequency|delivery schedule",
        "page action": r"checkout|see subscription options|choose a plan",
    },
    "operations": {
        "baseline rate": r"\b5(?:\.0+)?\s*(?:%|percent)",
        "measure named": r"checkout[ -]start|start.{0,16}checkout",
        "next measurement action": r"count|track|measure|monitor|baseline",
    },
}


def assess(desk, body):
    return {name: bool(re.search(pattern, body, flags=re.I | re.S)) for name, pattern in CASES[desk].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Generate new model output for the fictional cases")
    parser.add_argument("--baseline", action="store_true", help="Compare the original pipeline using the same live model")
    args = parser.parse_args()
    if args.baseline and not args.live:
        parser.error("--baseline requires --live")
    if args.live and not os.getenv("VEYS_MODEL"):
        parser.error("Set VEYS_MODEL to a served model first.")
    results = []
    with TemporaryDirectory() as tmp:
        for desk in CASES:
            brief = BRIEF if not args.live else BRIEF + "\nFocus on the " + desk + " deliverables."
            variants = ["managed", "baseline"] if args.baseline else ["managed"]
            for variant in variants:
                folder = Path(tmp) / f"{desk}-{variant}"
                create(folder, brief, "live" if args.live else "demo", desk if variant == "managed" else None)
                resume(folder)
                with closing(connect(folder)) as db:
                    if variant == "managed":
                        body = db.execute("SELECT body FROM steps WHERE id='editor'").fetchone()[0]
                    else:
                        body = "\n".join(row[0] for row in db.execute("SELECT content FROM drafts ORDER BY rowid"))
                results.append({"desk": desk, "variant": variant, "checks": assess(desk, body), "output": body})
    print(json.dumps({"mode": "model" if args.live else "offline fixture",
                      "model": os.getenv("VEYS_MODEL") if args.live else None,
                      "cases": results}, indent=2, ensure_ascii=False))
    return int(any(not all(row["checks"].values()) for row in results))


if __name__ == "__main__":
    sys.exit(main())
