from __future__ import annotations

import rich
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from typing import Any, Dict, Mapping, Mapping, Sequence, cast, List
from dataclasses import asdict

from kbdebugger.utils.json import write_json, now_utc_compact
from kbdebugger.vector.types import KeptQuality, NeighborHit

from .types import (
    NoveltyDecision,
    NeighborView,
    QualityNoveltyResult,
    QualityNoveltyResultRaw,
    QualityNoveltyInput,
)



def neighbor_hit_to_view(hit: NeighborHit) -> NeighborView | None:
    """
    Convert a rich NeighborHit into a slim NeighborView.

    Returns None if the KG sentence cannot be extracted.
    """
    relation = hit.get("relation")
    if not isinstance(relation, dict):
        return None

    edge = relation.get("edge")
    if not isinstance(edge, dict):
        return None

    props = edge.get("properties")
    if not isinstance(props, dict):
        return None

    sentence = props.get("sentence")
    if not isinstance(sentence, str) or not sentence.strip():
        return None

    score = float(hit.get("score", 0.0))
    return NeighborView(score=score, sentence=sentence.strip())


def kept_quality_to_novelty_input(
    kept: KeptQuality,
    *,
    top_k: int = 3,
) -> QualityNoveltyInput:
    """
    Convert VectorSimilarityFilter output (KeptQuality) into Novelty stage input
    (QualityNoveltyInput) with slim neighbors.

    Args:
        kept: KeptQuality from vector filter.
        top_k: How many neighbors to keep (default 3).

    Returns:
        QualityNoveltyInput ready to be fed to the novelty comparator.
    """
    quality = str(kept["quality"]).strip()
    max_score = float(kept["max_score"])

    views: List[NeighborView] = []
    for hit in kept["neighbors"][: max(1, top_k)]:
        view = neighbor_hit_to_view(hit)
        if view is not None:
            views.append(view)

    return QualityNoveltyInput(quality=quality, neighbors=views, max_score=max_score)


def _coerce_float_0_1(value: Any, *, field: str) -> float:
    """Parse float and validate [0,1]."""
    try:
        f = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Field '{field}' must be a number, got: {value!r}") from e
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"Field '{field}' must be within [0,1], got: {f}")
    return f


def coerce_quality_novelty_result(
        parsed: Mapping[str, Any],
        *,
        novelty_input: QualityNoveltyInput,
    ) -> QualityNoveltyResult:
    """
    Coerce parsed model JSON into a typed QualityNoveltyResult, enriched with
    the original quality + max_score from novelty_input.

    This function is intentionally forgiving:
    - If fields are missing, it falls back to safe defaults.
    - If decision is invalid, it defaults to PARTIALLY_NEW (safe behavior: keep signal).
    - Ensures confidence is in [0,1].
    """
    obj = cast(QualityNoveltyResultRaw, dict(parsed))

    decision_raw = str(obj.get("decision", "")).strip().upper()
    if decision_raw not in {d.value for d in NoveltyDecision}:
        rich.print(
            f"[coerce_quality_novelty_result] ⚠️ Invalid decision '{decision_raw}', defaulting to PARTIALLY_NEW."
        )
        # Safe default: treat as PARTIALLY_NEW to avoid dropping potential signal.
        decision = NoveltyDecision.PARTIALLY_NEW
    else:
        decision = NoveltyDecision(decision_raw)

    rationale = str(parsed.get("rationale", "No rationale provided.")).strip()

    novel_spans = obj.get("novel_spans")
    if not isinstance(novel_spans, list):
        novel_spans = []
    novel_spans = [str(s).strip() for s in novel_spans if str(s).strip()]

    matched = obj.get("matched_neighbor_sentence", None)
    if matched is not None and str(matched).strip():
        matched = str(matched).strip()
    else:
        matched = None

    confidence = _coerce_float_0_1(obj.get("confidence"), field="confidence")

    # Small consistency guard:
    # EXISTING should not claim novel spans; if it does, downgrade to PARTIALLY_NEW.
    if decision == NoveltyDecision.EXISTING and novel_spans:
        rich.print(
            "[coerce_quality_novelty_result] ⚠️ EXISTING result has novel_spans; downgrading to PARTIALLY_NEW."
        )
        decision = NoveltyDecision.PARTIALLY_NEW

    return QualityNoveltyResult(
        quality=novelty_input.quality,
        max_score=novelty_input.max_score,

        decision=decision,
        rationale=rationale,
        novel_spans=novel_spans,
        matched_neighbor_sentence=matched,
        confidence=confidence,
    )


# def save_novelty_results_json(
#     *,
#     kept: Sequence[KeptQuality],
#     results: Sequence[QualityNoveltyResult]
# ) -> str:
#     """
#     Write novelty comparator results to a readable JSON file.

#     JSON structure:
#     ```
#     {
#         "total": ...,
#         "counts": {"EXISTING": ..., "PARTIALLY_NEW": ..., "NEW": ...},
#         "created_at": "...",
#         "items": [
#             {
#                 "quality": "...",
#                 "max_score": 0.72,
#                 "decision": "PARTIALLY_NEW",
#                 "confidence": 0.78,
#                 "matched_neighbor_sentence": "...",
#                 "novel_spans": [...],
#                 "rationale": "..."
#             },
#             ...
#         ]
#     }
#     ```

#     Args:
#         kept: KeptQuality items, i.e., the output from vector filter stage.
#         results: Novelty results aligned with kept order. i.e., the output from novelty comparator LLM.

#     Returns:
#         The path written to disk.
#     """
#     created_at = now_utc_compact()

#     # Zip keeps things aligned and readable.
#     items: List[Mapping[str, object]] = []
#     counts = {"EXISTING": 0, "PARTIALLY_NEW": 0, "NEW": 0}

#     for k, r in zip(kept, results):
#         r_dict = asdict(r) # typed dataclass -> plain dict
#         decision = str(r_dict.get("decision", "")).upper()
#         if decision in counts:
#             counts[decision] += 1

#         items.append(
#             {
#                 "quality": k["quality"],
#                 "max_score": float(k["max_score"]),
#                 # Flatten the novelty result into the same object
#                 **r_dict,
#                 # "decision": r_dict.get("decision"),
#                 # "confidence": float(r_dict.get("confidence", 0.5)),
#                 # "matched_neighbor_sentence": r_dict.get("matched_neighbor_sentence"),
#                 # "novel_spans": r_dict.get("novel_spans", []),
#                 # "rationale": r_dict.get("rationale", ""),
#             }
#         )

#     total = len(items)
#     path = f"logs/04_novelty_comparator_results_{created_at}.json"

#     data: Mapping[str, object] = {
#         "total": total,
#         "counts": counts,
#         "created_at": created_at,
#         "items": items,
#     }

#     write_json(path, data)
#     print(f"\n[INFO] 🧠🧾 Wrote novelty comparator results to {path}")
#     return path


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
