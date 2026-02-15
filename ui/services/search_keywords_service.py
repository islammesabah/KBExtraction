"""
Search keywords loading service.

This module loads the curated list of Trustworthy-AI search
keywords from a packaged JSON resource inside `kbdebugger`.

Using importlib.resources
------------------------
This is robust for:
- editable installs
- packaging later
- running from different working directories
"""

from __future__ import annotations

import json
from importlib import resources
from typing import List


_RESOURCE_PACKAGE = "kbdebugger.resources"
_RESOURCE_NAME = "search_keywords.json"


def load_search_keywords() -> List[str]:
    """
    Load curated search keywords from packaged JSON resource.

    Returns
    -------
    list[str]
        List of allowed search keywords.

    Raises
    ------
    FileNotFoundError
        If resource file is missing.

    ValueError
        If JSON structure is invalid.
    """
    try:
        text = (
            resources.files(_RESOURCE_PACKAGE)
            .joinpath(_RESOURCE_NAME)
            .read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Resource {_RESOURCE_NAME!r} not found in package {_RESOURCE_PACKAGE!r}"
        )

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON format in {_RESOURCE_NAME}: {e}"
        ) from e

    if "keywords" not in data or not isinstance(data["keywords"], list):
        raise ValueError(
            f"{_RESOURCE_NAME} must contain a top-level 'keywords' list."
        )

    # Strip whitespace and remove empty entries
    keywords = [
        str(k).strip()
        for k in data["keywords"]
        if str(k).strip()
    ]

    return keywords
