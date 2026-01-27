from __future__ import annotations

from importlib.resources import files
from string import Template
from functools import lru_cache
import json

@lru_cache(maxsize=32) # disk read happens once per template. 32 means up to 32 different templates cached.
def _load_template(name: str) -> Template:
    """
    Load a prompt template from kbdebugger/prompts/<name>.txt
    and wrap it as a string.Template.
    """
    path = files("kbdebugger.prompts").joinpath(f"{name}.txt")
    text = path.read_text(encoding="utf-8")
    return Template(text) 
    # Template is a wrapper around str with $var substitution. 
    # e.g., Template("Hello $name") will replace $name with the value provided


@lru_cache(maxsize=1)
def load_json_resource(name: str):
    """
    Load a JSON file from kbdebugger/prompts/<name>.json
    and return the parsed Python object.
    """
    path = files("kbdebugger.prompts.examples").joinpath(f"{name}.json")
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def render_prompt(name: str, **kwargs) -> str:
    """
    Render a named prompt template with the given variables.

    Usage:
    ```
    render_prompt("triplets_single", sentence_json=...)
    render_prompt("triplets_batch", payload_json=...)
    ```
    """
    tmpl = _load_template(name)
    return tmpl.safe_substitute(**kwargs) 
    # safeSubstitute so that missing vars won't crash
