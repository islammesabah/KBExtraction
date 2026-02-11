from __future__ import annotations

"""
Run-level timing utilities for the KBDebugger pipeline.

Goal
----
We want to measure and record how long each pipeline stage takes, without
polluting `pipeline/run.py` with timing logic.

This module provides:

1) RunTimer
   - collects per-stage timings
   - can dump a single JSON file for the whole run

2) timed_stage(...)
   - a context manager that:
       - shows a Rich spinner (nice UX for blocking stages)
       - measures elapsed time using time.perf_counter()
       - registers stage timing into a RunTimer

Design constraints
------------------
- Lightweight (Rich only; no external tracing frameworks)
- Stable output structure (so we can diff across runs)
- Works for both:
    - blocking single-call stages (Docling, Neo4j retrieval, LLM calls)
    - loops (we can still use rich.track inside loops)
"""

from dataclasses import dataclass, field
from contextlib import contextmanager
from time import perf_counter
from typing import Any, Dict, Iterator, Optional

from rich.console import Console
from rich.status import Status

from kbdebugger.utils.json import write_json
from kbdebugger.utils.time import now_utc_compact
from .time import _format_seconds_human, now_utc_iso


@dataclass
class StageTiming:
    """
    Timing record for a single stage.
    """
    name: str
    elapsed_seconds: float
    elapsed_human: str
    started_at_utc: str
    finished_at_utc: str


@dataclass
class RunTimer:
    """
    Collect timings for an entire pipeline run.

    Typical usage
    -------------
    >>> timer = RunTimer(run_name="kbdebugger_pipeline")
    >>> with timer.stage("KG retrieval"):
    ...     kg = retrieve_keyword_subgraph(...)
    >>> timer.save_json()
    """

    run_name: str = "kbdebugger_pipeline"
    created_at_utc: str = field(default_factory=lambda: now_utc_iso())
    stages: Dict[str, StageTiming] = field(default_factory=dict)

    def record(
        self,
        *,
        stage_name: str,
        started_at_utc: str,
        finished_at_utc: str,
        elapsed_seconds: float,
    ) -> None:
        """
        Record a completed stage timing.

        Notes
        -----
        - If a stage name is reused, the last timing wins.
          (This is usually what we want when rerunning a stage in one run.)
        """
        self.stages[stage_name] = StageTiming(
            name=stage_name,
            elapsed_seconds=float(elapsed_seconds),
            elapsed_human=_format_seconds_human(elapsed_seconds),
            started_at_utc=started_at_utc,
            finished_at_utc=finished_at_utc,
        )

    def as_json_dict(self) -> Dict[str, Any]:
        """
        Produce a stable JSON-serializable structure for saving/logging.
        """
        # Keep insertion order in Python 3.7+ dicts; but we also sort by name for stability.
        stages_sorted = {k: vars(self.stages[k]) for k in sorted(self.stages.keys())}
        total_seconds = sum(t.elapsed_seconds for t in self.stages.values())

        return {
            "run_name": self.run_name,
            "created_at_utc": self.created_at_utc,
            "total_elapsed_seconds": float(total_seconds),
            "total_elapsed_human": _format_seconds_human(total_seconds),
            "stages": stages_sorted,
        }

    def save_json(
        self,
        *,
        path: Optional[str] = None,
        prefix: str = "logs/00_pipeline_timing",
    ) -> str:
        """
        Save a single JSON file for the entire run.

        Parameters
        ----------
        path:
            Optional explicit file path. If not provided, we generate one.

        prefix:
            Default prefix used when autogenerating a filename.

        Returns
        -------
        str
            The path written.
        """
        if path is None:
            created_at = now_utc_compact()
            path = f"{prefix}_{created_at}.json"

        write_json(path, self.as_json_dict())
        return path

    @contextmanager
    def stage(
        self,
        title: str,
        *,
        console: Optional[Console] = None,
        show_spinner: bool = False,
        spinner: str = "dots",
        print_done: bool = True,
    ) -> Iterator[None]:
        """
        Context manager: show a spinner + measure + record timing.

        This is the "one-liner" you wrap around each pipeline stage.

        Example
        -------
        >>> with timer.stage("🦆 Docling: PDF → paragraphs"):
        ...     paragraphs = extract_paragraphs_from_pdf(...)
        """
        c = console or Console()
        started_at = now_utc_iso() # e.g., "2026-02-11T15:26:55"
        t0 = perf_counter()

        if show_spinner:
            with Status(title, console=c, spinner=spinner):
                yield
        else:
            # No status UI — timing only.
            yield

        elapsed = perf_counter() - t0
        finished_at = now_utc_iso()

        self.record(
            stage_name=title,
            started_at_utc=started_at,
            finished_at_utc=finished_at,
            elapsed_seconds=elapsed,
        )

        if print_done:
            self.console.print(
                f"[green]✅ {title}[/green] [dim](took {_format_seconds_human(elapsed)})[/dim]"
            )
