"""Hermes command for producing a client draft with the active profile's model."""
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4, UUID

from .provider import messages
from .teams import DESKS, plan_schema
from .workflow import create, render, resume

USAGE = "/veys <agency|sales|studio|delivery|operations> <client brief>\n/veys resume <run-id>"


def register(ctx):
    from plugins.plugin_storage import plugin_data_dir

    def model(agent, brief, drafts):
        turns = messages(agent, brief, drafts)
        if agent.name == "manager" and os.getenv("VEYS_PLAN_FORMAT") == "schema":
            result = ctx.llm.complete_structured(
                instructions=turns[0]["content"], input=[{"type": "text", "text": turns[1]["content"]}],
                json_schema=plan_schema(brief, drafts["roster"], repair="repair" in drafts), schema_name="agency_plan", purpose="veys.manager", timeout=240)
        else:
            result = ctx.llm.complete(messages=turns, purpose=f"veys.{agent.name}", timeout=240)
        return result.text

    def command(raw_args, *, platform="", source=None, session_key=""):
        parts = raw_args.strip().split(None, 1)
        if len(parts) != 2 or parts[0] not in (*DESKS, "resume"):
            return USAGE
        actor = getattr(source, "user_id", "") if source else ""
        if platform in {"cli", "tui", "desktop", "local"} and not actor:
            actor = "local"
        if not actor or not platform:
            return "Hermes could not identify the caller. Use a signed-in chat or the Veys CLI."
        scope = [platform, str(actor), str(getattr(source, "chat_id", "") or ""), session_key]
        owner = hashlib.sha256(json.dumps(scope).encode()).hexdigest()
        root = Path(plugin_data_dir("veys")) / owner
        action, argument = parts
        if action == "resume":
            try:
                run_id = UUID(argument).hex
            except ValueError:
                return USAGE
            directory = root / run_id
            if not (directory / "run.sqlite3").is_file():
                return "Run not found in this conversation."
        else:
            if len(argument) > 32000:
                return "Shorten the brief to 32,000 characters."
            run_id = uuid4().hex
            directory = root / run_id
            create(directory, argument, "live", action)
        try:
            resume(directory, model)
        except Exception as exc:
            # Provider/SDK exception strings can contain private request data.
            reason = ("Veys could not validate a team draft." if isinstance(exc, ValueError)
                      else "The model or run storage is unavailable.")
            return f"Run {run_id} paused. {reason} Retry here with /veys resume {run_id}."
        return f"Veys run {run_id}\n\n{render(directory, final_only=True)}"

    ctx.register_command("veys", handler=command, description="Draft an agency work pack", args_hint="<team> <brief>")
