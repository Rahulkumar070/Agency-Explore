"""Local request/response files for an operator or external agent host."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .provider import messages


class WaitingForReplies(Exception):
    pass


def exchange(directory, agent, brief, context):
    requests = directory / "requests"
    responses = directory / "responses"
    requests.mkdir(exist_ok=True)
    responses.mkdir(exist_ok=True)
    request = requests / f"{agent.name}.json"
    if not request.exists():
        with NamedTemporaryFile(dir=requests, mode="w", encoding="utf-8", delete=False) as stream:
            temporary = Path(stream.name)
            try:
                json.dump(messages(agent, brief, context), stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        temporary.replace(request)
    reply = responses / f"{agent.name}.txt"
    if not reply.is_file():
        raise WaitingForReplies(f"Read {request} and save the response in {reply}")
    with reply.open(encoding="utf-8") as stream:
        return stream.read(100_001)
