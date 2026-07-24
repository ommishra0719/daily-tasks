"""
System-prompt registry.

Loads named system-prompt configurations from `app/prompts.yaml` (path is
configurable via `settings.PROMPTS_FILE`, so tests can point at a fixture
file). The rest of the app only ever looks a prompt up **by name** -- there
is intentionally no code path that accepts free-form system-prompt text
from an end user. That is the multi-tenant safety property this module
exists to guarantee.
"""

from functools import lru_cache

import yaml

from app.config import settings


class UnknownPromptError(KeyError):
    """Raised when a prompt_name doesn't exist in the registry."""


@lru_cache
def _load_registry() -> dict[str, dict]:
    with open(settings.PROMPTS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("prompts", {})


def clear_cache() -> None:
    """Used by tests when swapping in a different PROMPTS_FILE."""
    _load_registry.cache_clear()


def list_prompts() -> dict[str, str]:
    """Returns {prompt_name: description} for every registered prompt."""
    return {name: cfg.get("description", "") for name, cfg in _load_registry().items()}


def get_system_prompt(prompt_name: str) -> str:
    """
    Resolve a prompt_name to its system-prompt text.

    Raises UnknownPromptError if prompt_name isn't registered -- callers
    (the sessions router) turn that into an HTTP 400 with the list of valid
    names, rather than silently falling back to something else.
    """
    registry = _load_registry()
    if prompt_name not in registry:
        raise UnknownPromptError(prompt_name)
    return registry[prompt_name]["system_prompt"].strip()
