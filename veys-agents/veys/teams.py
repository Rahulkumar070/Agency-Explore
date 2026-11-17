"""Load original specialist definitions and freeze the selected roster for each run."""
import json
import re
import tomllib
from importlib.resources import files

DESKS = ("agency", "sales", "studio", "delivery", "operations")
MAX_SPECIALISTS = 4


def roster(desk):
    if desk not in DESKS:
        raise ValueError(f"Unknown desk: {desk}")
    records = tomllib.loads(files(__package__).joinpath("catalog/specialists.toml").read_text("utf-8"))["role"]
    result = {}
    for role in records:
        name = role["name"]
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", name) or name in result or name in {"manager", "reviewer", "editor"}:
            raise ValueError(f"Invalid or repeated specialist ID: {name}")
        if role["desk"] not in DESKS[1:] or not role["instructions"].strip() or not role["title"].strip():
            raise ValueError(f"Incomplete role: {name}")
        result[name] = role
    return {name: role for name, role in result.items() if desk == "agency" or role["desk"] == desk}


def plan_schema(brief, roles, *, repair=False):
    # Constrain a small model to grounded spans that also pass the ordinary validator.
    evidence = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", brief.strip()):
        for start in range(0, len(sentence), 400):
            quote = sentence[start:start + 400].strip()
            if quote:
                evidence.append(quote)
    item = {"type": "object", "properties": {
        "role": {"type": "string", "enum": list(roles)},
        "task": {"type": "string", "minLength": 1, "maxLength": 1200},
        "evidence": {"type": "string", "enum": list(dict.fromkeys(evidence))}},
        "required": ["role", "task", "evidence"], "additionalProperties": False}
    return {"type": "object", "properties": {"assignments": {
        "type": "array", "minItems": 1, "maxItems": 1 if repair else min(len(roles), MAX_SPECIALISTS), "items": item}},
        "required": ["assignments"], "additionalProperties": False}


def read_plan(raw, roles, brief):
    text = raw.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    try:
        assignments = json.loads(text)["assignments"]
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("Manager must return a JSON object containing assignments.") from exc
    if not isinstance(assignments, list) or not 1 <= len(assignments) <= MAX_SPECIALISTS:
        raise ValueError(f"Select between 1 and {MAX_SPECIALISTS} specialists.")
    seen = set()
    for item in assignments:
        if not isinstance(item, dict) or set(item) != {"role", "task", "evidence"}:
            raise ValueError("Each assignment needs exactly role, task and evidence.")
        if not all(isinstance(v, str) and v.strip() for v in item.values()):
            raise ValueError("Assignment fields must be nonempty strings.")
        name = item["role"]
        if name not in roles or name in seen:
            raise ValueError(f"Unknown or repeated specialist: {name}")
        if len(item["task"]) > 1200 or len(item["evidence"]) > 600 or item["evidence"] not in brief:
            raise ValueError("Use a task under 1201 characters and a short exact quote from the brief.")
        seen.add(name)
    return assignments


MANAGER = """Choose one to four distinct specialists from the supplied roster for this brief.
Delegate only the work needed. Assign each a concrete, independently achievable deliverable.
Return exactly one JSON object with an assignments array. Each item has three string fields:
role (exact roster ID), task (at most 1200 characters) and evidence (an exact contiguous
quote of at most 600 characters copied from the original brief that motivates this task)."""

REVIEWER = """Compare each specialist deliverable against its assignment and the original brief.
Quote the specific unsupported claim or omission and name its role. Check fee versus budget,
promised dates and fabricated metrics. Give a concrete correction for each issue, or state
which checks passed. This is internal editorial feedback."""

EDITOR = """Prepare the finished agency work pack. Use the specialist deliverables and
apply the reviewer's corrections. Keep usable copy, deliverables, owners, and acceptance
tests when relevant. Resolve contradictions against the brief. Separate confirmed client
facts, proposed work and unanswered questions. Close with the next decision."""
