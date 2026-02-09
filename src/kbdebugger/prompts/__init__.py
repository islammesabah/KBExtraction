from __future__ import annotations
from typing import Any, Mapping, Optional

"""
Prompt loading and prompt-building utilities.

This package provides:
- Fast prompt template loading from package resources
- JSON examples loading from `kbdebugger.prompts.examples`
- Convenience helpers to construct prompts with:
    - few-shot examples (optional)
    - typed inputs (dataclasses) or JSON-serializable objects

Why this exists
---------------
Many pipeline stages follow the same pattern:

1) Load a prompt template from `kbdebugger/prompts/<name>.txt`
2) Optionally load few-shot examples from `kbdebugger/prompts/examples/<name>.json`
3) Serialize examples and inputs as JSON strings
4) Inject them into the prompt template variables

Without a central helper, this repetitive logic tends to spread across:
- decomposers
- triplet extractors
- novelty comparators
- any future LLM stage

The `build_prompt` helper below standardizes this pattern so call sites remain tiny and
consistent, and we can enforce the same JSON serialization and conventions everywhere.
"""


from dataclasses import asdict, is_dataclass
from importlib.resources import files
from string import Template
from functools import lru_cache
import json


# ---------------------------------------------------------------------------
# Internal resource loaders (cached)
# ---------------------------------------------------------------------------
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



# ---------------------------------------------------------------------------
# JSON shaping helpers
# ---------------------------------------------------------------------------
def _to_jsonable(obj: Any) -> Any:
    """
    Convert an object into something JSON-serializable.

    Supported inputs
    ----------------
    - dataclass instances -> converted using dataclasses.asdict
    - mappings/lists/strings/numbers -> passed through
    - other objects -> returned as-is (json.dumps may fail)

    Parameters
    ----------
    obj:
        Any Python object.

    Returns
    -------
    Any
        A JSON-serializable representation when possible.
    """
    if is_dataclass(obj):
        # convert dataclass to dict for JSON serialization
        return asdict(obj) # type: ignore 
    return obj


def _dumps_json(obj: Any) -> str:
    """
    Serialize an object to a JSON string using project conventions.

    Conventions
    -----------
    - ensure_ascii=False (preserve unicode for readability)
    - no pretty-print by default (compact prompts)
    - stable key ordering is NOT enforced here (not required for LLM)

    Parameters
    ----------
    obj:
        JSON-serializable object.

    Returns
    -------
    str
        JSON string.
    """
    return json.dumps(obj, ensure_ascii=False)


# ---------------------------------------------------------------------------
# High-level prompt builder(s)
# ---------------------------------------------------------------------------
def build_prompt(
    *,
    prompt_name: str,
    input_obj: Any,
    input_var: str = "input_json",

    examples_name: Optional[str] = None,
    examples_var: str = "examples_json",
    
    include_examples: bool = True,
    extra_vars: Optional[Mapping[str, Any]] = None,
) -> str:
    """
    Build a prompt using a standard "examples + input" convention.

    This function is meant to replace repeated boilerplate like:

        examples = load_json_resource("quality_novelty_comparator")
        examples_json = json.dumps(examples, ensure_ascii=False)
        input_json = json.dumps(asdict(item), ensure_ascii=False)
        return render_prompt("quality_novelty_comparator",
                             examples_json=examples_json,
                             input_json=input_json)

    Parameters
    ----------
    prompt_name:
        Name of the prompt template file (without extension), e.g.:
            "quality_novelty_comparator"
            "chunk_decompose_batch"

    input_obj:
        The input payload to inject into the prompt.
        Can be a dataclass, dict, list, or other JSON-serializable structure.

    input_var:
        The template variable name used in the prompt template for the input JSON.
        Defaults to "input_json" to match your existing comparator prompt.

        Example:
            If your template contains `$input_json`, keep the default.
            If your template contains `$chunks_json`, set input_var="chunks_json".

    examples_name:
        The examples JSON filename (without extension) under `kbdebugger/prompts/examples/`.

        If None:
            defaults to `prompt_name` (convention-based).

    examples_var:
        The template variable name used for examples JSON.
        Defaults to "examples_json".

    include_examples:
        If True, load and inject examples JSON.
        If False, do not load examples and do not set examples_var.

        This supports templates that do not use examples at all.

    extra_vars:
        Additional template variables to pass through to `render_prompt`.
        Useful for variables like `max_qualities_per_chunk`, `schema_json`, etc.

    Returns
    -------
    str
        The rendered prompt string.

    Raises
    ------
    FileNotFoundError
        If `include_examples=True` and the examples file does not exist.

    TypeError
        If input_obj cannot be serialized by json.dumps.

    Notes
    -----
    This function intentionally does not validate that the prompt actually references
    `$input_var` or `$examples_var`. The underlying `safe_substitute` would simply
    leave placeholders unchanged if missing.
    """
    vars_out: dict[str, Any] = {}

    # --- examples (optional) ---
    if include_examples:
        ex_name = examples_name or prompt_name
        examples_obj = load_json_resource(ex_name)
        vars_out[examples_var] = _dumps_json(_to_jsonable(examples_obj))

    # --- input payload ---
    vars_out[input_var] = _dumps_json(_to_jsonable(input_obj))

    # --- any extra template vars ---
    if extra_vars:
        vars_out.update(dict(extra_vars))

    return render_prompt(prompt_name, **vars_out)


def build_prompt_batch(
    *,
    prompt_name: str,
    items: Any,
    items_var: str = "items_json",
    wrapper_key: str = "items",

    examples_name: Optional[str] = None,
    examples_var: str = "examples_json",
    
    include_examples: bool = True,
    extra_vars: Optional[Mapping[str, Any]] = None,
) -> str:
    """
    Build a prompt for the common "batched items" pattern.

    Many batched prompts use a wrapper structure like:
        {"items": [ ... ]}

    This helper standardizes that pattern and reduces call-site boilerplate.

    Parameters
    ----------
    prompt_name:
        Prompt template name without extension.

    items:
        A sequence of items (dataclasses/dicts) that will be wrapped under `wrapper_key`.

    items_var:
        Template variable name for the JSON payload (defaults to "items_json").

    wrapper_key:
        JSON key used to wrap the list of items (defaults to "items").

        Example:
            wrapper_key="chunks" -> {"chunks":[...]} injected into `$items_json`.

    examples_name / examples_var / include_examples:
        Same meaning as in `build_prompt`.

    extra_vars:
        Extra template variables.

    Returns
    -------
    str
        Rendered prompt text.
    """
    payload = {wrapper_key: _to_jsonable(items)}
    return build_prompt(
        prompt_name=prompt_name,
        input_obj=payload,
        input_var=items_var,
        examples_name=examples_name,
        examples_var=examples_var,
        include_examples=include_examples,
        extra_vars=extra_vars,
    )
