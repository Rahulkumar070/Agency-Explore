"""Short-lived private llama.cpp server for a Veys workflow."""
import os
from contextlib import contextmanager
from functools import partial
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from .provider import generate
from .providers import Settings


def default_model():
    return Path(__file__).resolve().parents[1] / "models/qwen2.5-1.5b-instruct-q4_k_m.gguf"


@contextmanager
def local_model(model):
    if not model.is_file() or not shutil.which("llama-server"):
        raise ValueError("Supply a GGUF model and install llama-server on PATH.")
    with tempfile.TemporaryDirectory(prefix="veys-model-") as temp:
        key = secrets.token_urlsafe(32)
        key_file = Path(temp) / "key"
        key_file.write_text(key)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        command = ["llama-server", "-m", str(model), "--alias", "veys-local", "--host", "127.0.0.1",
                   "--port", str(port), "--api-key-file", str(key_file), "--device", "none", "-ngl", "0",
                   "-c", "12288", "--parallel", "2", "--temp", "0.2", "--seed", "7",
                   "--repeat-penalty", "1.12", "--repeat-last-n", "256"]
        with (Path(temp) / "server.log").open("wb") as log:
            server = subprocess.Popen(command, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 120
                while server.poll() is None and time.monotonic() < deadline:
                    try:
                        request = Request(base + "/v1/models", headers={"Authorization": f"Bearer {key}"})
                        with urlopen(request, timeout=2) as response:
                            if response.status == 200:
                                break
                    except (URLError, TimeoutError):
                        time.sleep(0.3)
                else:
                    raise ValueError("Local model failed to start. Check llama-server and the GGUF file.")
                yield partial(generate, structured=True, concise=True, config=Settings("custom", base + "/v1", "veys-local", "chat", key))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
