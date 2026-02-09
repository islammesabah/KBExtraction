from kbdebugger.vector.types import KeptQuality
import rich
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from dataclasses import asdict
from typing import Dict, Mapping, Mapping, Sequence, List
from kbdebugger.utils.json import write_json, now_utc_compact

from .types import (
    NoveltyDecision,
    QualityNoveltyResult,
)

def save_novelty_results_json(results: Sequence[QualityNoveltyResult]) -> str:
    """
    Write novelty comparator results to a readable JSON file.

    JSON structure:
    {
      "total": ...,
      "counts": {"EXISTING": ..., "PARTIALLY_NEW": ..., "NEW": ...},
      "created_at": "...",
      "items": [
        {
          "quality": "...",
          "max_score": 0.72,
          "decision": "PARTIALLY_NEW",
          "confidence": 0.78,
          "matched_neighbor_sentence": "...",
          "novel_spans": [...],
          "rationale": "..."
        }
      ]
    }

    Args:
        results: Novelty results (each already carries its quality context).

    Returns:
        The path written to disk.
    """
    created_at = now_utc_compact()

    counts = {"EXISTING": 0, "PARTIALLY_NEW": 0, "NEW": 0}
    items: List[Mapping[str, object]] = []

    for r in results:
        decision_str = str(r.decision)  # relies on NoveltyDecision.__str__ -> value
        decision_key = decision_str.upper()
        if decision_key in counts:
            counts[decision_key] += 1

        d = asdict(r)

        # Make JSON serialization 100% deterministic/robust:
        d["decision"] = decision_str # so that enum becomes string
        d["novel_spans"] = list(r.novel_spans) # ensure list, not other Sequence

        items.append(d)

    path = f"logs/04_novelty_comparator_results_{created_at}.json"

    data: Mapping[str, object] = {
        "total": len(results),
        "counts": counts,
        "created_at": created_at,
        "results": items,
    }

    write_json(path, data)
    print(f"\n[INFO] 🧠🧾 Wrote novelty comparator results to {path}")
    return path


def pretty_print_novelty_results(
    *,
    kept: Sequence[KeptQuality],
    results: Sequence[QualityNoveltyResult],
    title: str = "Novelty Comparator Results",
    max_items_to_show: int | None = None,
    console: Console | None = None,
) -> None:
    """
    Pretty-print novelty comparator results using rich.

    Parameters
    ----------
    kept:
        Kept qualities produced by the Vector Similarity Filter.
        (We use these for quality text + max_score only; we do not show neighbors here.)

    results:
        Novelty comparator results aligned with `kept` order.

    title:
        Title shown at the top of the output.

    max_items_to_show:
        Optional cap on how many items to display (useful for large runs).
        If None, prints all.

    console:
        Optional rich Console. If None, a new Console is created.
    """
    c = console or Console()

    n = min(len(kept), len(results))
    if max_items_to_show is not None:
        n = min(n, max(0, int(max_items_to_show)))

    c.rule(f"[bold cyan]{title}[/bold cyan]")

    if n == 0:
        c.print("[yellow]No novelty results to display.[/yellow]")
        return

    # ----------------------------
    # Summary counts
    # ----------------------------
    counts: Dict[str, int] = {"EXISTING": 0, "PARTIALLY_NEW": 0, "NEW": 0}
    for r in results[:n]:
        # With __str__ overridden on NoveltyDecision, this is safe and clean.
        key = str(r.decision).upper()
        if key in counts:
            counts[key] += 1

    summary = (
        f"[bold]Total shown:[/bold] {n}\n"
        f"[bold green]NEW:[/bold green] {counts['NEW']}    "
        f"[bold yellow]PARTIALLY_NEW:[/bold yellow] {counts['PARTIALLY_NEW']}    "
        f"[bold red]EXISTING:[/bold red] {counts['EXISTING']}"
    )
    c.print(Panel(summary, border_style="cyan", padding=(1, 2)))

    # ----------------------------
    # Group by decision (optional sections)
    # ----------------------------
    # We print in original order by default (more helpful for tracing),
    # but we add a per-item colored border and header.
    c.print(Rule("[bold]📌 Per-quality novelty decisions[/bold]"))

    for i in range(n):
        k = kept[i]
        r = results[i]

        quality = str(k["quality"])
        max_score = float(k["max_score"])
        decision = str(r.decision)  # thanks to __str__ override
        conf = float(r.confidence)

        # Color coding
        if r.decision == NoveltyDecision.NEW:
            border = "green"
            badge = "🆕 NEW"
            badge_style = "bold green"
        elif r.decision == NoveltyDecision.PARTIALLY_NEW:
            border = "yellow"
            badge = "🧩 PARTIALLY_NEW"
            badge_style = "bold yellow"
        else:
            border = "red"
            badge = "♻️ EXISTING"
            badge_style = "bold red"

        header = Text()
        header.append(f"[{i+1}] ", style="bold cyan")
        header.append(badge, style=badge_style)
        header.append("  ")
        header.append(f"(max_score={max_score:.3f}, confidence={conf:.2f})", style="dim")

        body_lines: List[str] = []
        body_lines.append(f"[bold]Quality:[/bold] {quality}")
        body_lines.append(f"[bold]Decision:[/bold] {decision}")
        body_lines.append(f"[bold]Rationale:[/bold] {r.rationale}")

        if r.novel_spans:
            spans = ", ".join(f"[magenta]{s}[/magenta]" for s in r.novel_spans)
            body_lines.append(f"[bold]Novel spans:[/bold] {spans}")
        else:
            body_lines.append("[bold]Novel spans:[/bold] [dim](none)[/dim]")

        if r.matched_neighbor_sentence:
            body_lines.append(
                f"[bold]Matched neighbor sentence:[/bold] {r.matched_neighbor_sentence}"
            )
        else:
            body_lines.append("[bold]Matched neighbor sentence:[/bold] [dim](none)[/dim]")

        c.print(
            Panel(
                "\n".join(body_lines),
                title=header,
                border_style=border,
                padding=(1, 2),
            )
        )
