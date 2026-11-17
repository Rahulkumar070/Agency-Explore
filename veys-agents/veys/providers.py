"""Provider destinations and their credential boundaries."""
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Provider:
    url: str
    key_env: str = ""
    protocol: str = "chat"


PROVIDERS = {
    "openai": Provider("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "anthropic": Provider("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "messages"),
    "gemini": Provider("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "openrouter": Provider("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "groq": Provider("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "deepseek": Provider("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
    "mistral": Provider("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    "xai": Provider("https://api.x.ai/v1", "XAI_API_KEY"),
    "together": Provider("https://api.together.ai/v1", "TOGETHER_API_KEY"),
    "fireworks": Provider("https://api.fireworks.ai/inference/v1", "FIREWORKS_API_KEY"),
    "ollama": Provider("http://127.0.0.1:11434/v1"),
    "lmstudio": Provider("http://127.0.0.1:1234/v1"),
    "custom": Provider("http://127.0.0.1:11434/v1"),
}


@dataclass(frozen=True)
class Settings:
    name: str
    url: str
    model: str
    protocol: str
    key: str = field(repr=False)


def endpoint(name, override):
    if name not in PROVIDERS:
        raise ValueError("Unknown VEYS_PROVIDER. Run 'veys providers' for the list.")
    provider = PROVIDERS[name]
    override = override.strip().rstrip("/")
    if name != "custom" and override and override != provider.url:
        raise ValueError("Unset VEYS_BASE_URL for this preset, or use VEYS_PROVIDER=custom.")
    url = override or provider.url
    base = urlsplit(url)
    if not base.hostname or base.username is not None or base.password is not None or base.query or base.fragment:
        raise ValueError("VEYS_BASE_URL must be an API base URL without credentials, query or fragment.")
    if base.scheme != "https" and not (base.scheme == "http" and base.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("Use HTTPS for a remote endpoint, or HTTP on loopback.")
    return url


def settings(ask_key=False, *, selection=None):
    if selection:
        name, model = selection["provider"], selection["model"]
        url = endpoint(name, selection.get("url", ""))
    else:
        name = os.getenv("VEYS_PROVIDER", "custom").strip().lower()
        url = endpoint(name, os.getenv("VEYS_BASE_URL", ""))
        model = os.getenv("VEYS_MODEL", "").strip()
    provider = PROVIDERS[name]
    if not model:
        raise ValueError("Set VEYS_MODEL to the model ID served by your endpoint.")
    key_env = provider.key_env or "VEYS_API_KEY"
    key = os.getenv(key_env, "")
    if ask_key:
        import getpass
        import sys
        if not sys.stdin.isatty():
            raise ValueError("--ask-key requires an interactive terminal.")
        key = getpass.getpass(f"API key for {name} (hidden): ").strip()
    if provider.key_env and not key:
        raise ValueError(f"Set {key_env} or use --ask-key.")
    if any(ord(c) <= 32 or ord(c) >= 127 for c in key):
        raise ValueError("The API key contains invalid characters.")
    return Settings(name, url, model, provider.protocol, key)
