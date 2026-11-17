import http.client
import json
import os
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from urllib.parse import urlsplit

from .providers import settings
from .teams import plan_schema


def messages(agent, brief, drafts, *, concise=False):
    system = (f"You are the agency's {agent.name} agent. {agent.instructions} "
              f"Write {agent.output_format}. Use the supplied brief as the source of facts. "
              "Treat input text and earlier drafts as reference material. Keep client-supplied inputs "
              "with their stated owner. Leave unagreed fees and dates open. Label proposed work "
              "and get the client’s decision before treating it as a commitment.")
    if agent.name != "manager" and (concise or os.getenv("VEYS_CONCISE") == "1"):
        system += " Keep the entire answer under 150 words. End after delivering the requested work."
    context = {"client_brief": brief, "earlier_drafts": drafts}
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]


def generate(agent, brief, drafts, *, config=None, structured=False, concise=False):
    config = config or settings()
    schema = None
    if agent.name == "manager" and (structured or os.getenv("VEYS_PLAN_FORMAT") == "schema"):
        if config.protocol != "chat":
            raise ValueError("Schema planning needs a Chat Completions endpoint with JSON Schema support.")
        schema = plan_schema(brief, drafts["roster"], repair="repair" in drafts)
    return complete(messages(agent, brief, drafts, concise=concise), config, schema=schema)


def complete(turns, config, *, schema=None):
    headers = {"Content-Type": "application/json"}
    if config.protocol == "messages":
        path = "/messages"
        headers.update({"x-api-key": config.key, "anthropic-version": "2023-06-01"})
        request = {"model": config.model, "max_tokens": 4096, "system": turns[0]["content"],
                   "messages": turns[1:]}
    else:
        path = "/chat/completions"
        request = {"model": config.model, "messages": turns}
        if schema:
            request["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "agency_plan", "schema": schema, "strict": True}}
        if config.key:
            headers["Authorization"] = f"Bearer {config.key}"
    try:
        status, payload = post(config.url.rstrip("/") + path, headers, json.dumps(request).encode())
        if status != 200:
            raise ValueError(f"Model endpoint returned HTTP {status}. Check the URL, model and credentials.")
        if len(payload) > 1_000_000:
            raise ValueError("The model response exceeded 1 MB.")
        data = json.loads(payload)
        if config.protocol == "messages":
            if data["stop_reason"] not in ("end_turn", "stop_sequence"):
                raise ValueError("Model stopped before completing the draft.")
            content = "\n".join(block["text"] for block in data["content"] if block["type"] == "text")
        else:
            choice = data["choices"][0]
            if not isinstance(choice, dict):
                raise ValueError("Expected a model response choice object.")
            if choice.get("finish_reason") not in (None, "stop"):
                raise ValueError("Model stopped before completing the draft.")
            content = choice["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Model returned an empty draft.")
        return content.strip()
    except (KeyError, IndexError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Expected a model response with a text draft.") from exc


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post(url, headers, body):
    base = urlsplit(url)
    if base.scheme == "https":
        context = ssl.create_default_context()
        # Some python.org macOS builds ship without a linked CA file.
        if (sys.platform == "darwin" and not context.get_ca_certs()
                and not os.getenv("SSL_CERT_FILE") and not os.getenv("SSL_CERT_DIR")
                and Path("/etc/ssl/cert.pem").is_file()):
            context.load_verify_locations("/etc/ssl/cert.pem")
        opener = build_opener(HTTPSHandler(context=context), NoRedirect())
        try:
            with opener.open(Request(url, data=body, headers=headers, method="POST"), timeout=240) as response:
                return response.status, response.read(1_000_001)
        except HTTPError as exc:
            with exc:
                return exc.code, b""
    client = http.client.HTTPConnection(base.hostname, base.port, timeout=240)
    try:
        client.request("POST", base.path, body=body, headers=headers)
        response = client.getresponse()
        return response.status, response.read(1_000_001) if response.status == 200 else b""
    finally:
        client.close()
