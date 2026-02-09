from __future__ import annotations

"""
Progress and timing helpers.

This module provides small utilities to improve the user experience of long-running
pipeline stages by emitting:
- stage start/end messages
- elapsed time
- optional spinner UI while blocking library calls run

We intentionally keep this lightweight and dependency-minimal (Rich only).
"""

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator, Optional

from rich.console import Console
from rich.status import Status


@contextmanager
def stage_status(
    title: str,
    *,
    console: Optional[Console] = None,
    spinner: str = "dots",
) -> Iterator[None]:
    """
    Context manager that shows a Rich spinner and prints elapsed time.

    Use this for stages where work happens inside a single blocking call
    (e.g., Docling loader.load()) and you cannot expose per-item progress.

    Parameters
    ----------
    title:
        Human readable stage label shown in the console.

    console:
        Rich Console instance. If None, a default Console is created.

    spinner:
        Rich spinner name. Examples: "dots", "earth", "bouncingBall".

    Example
    -------
    >>> with stage_status("🦆 Docling: PDF → paragraphs"):
    ...     docs = loader.load()
    """
    c = console or Console()
    start = perf_counter()

    with Status(title, console=c, spinner=spinner):
        yield

    elapsed = perf_counter() - start
    c.print(f"[green]✅ {title}[/green] [dim](took {elapsed:.2f}s)[/dim]")
