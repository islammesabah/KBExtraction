"""
Seed importer for AuraDB that *reuses the pipeline upsert logic*.

It:
1) Reads a semicolon-separated CSV: source;relationship;destination
2) Converts each row into a GraphRelation
3) Calls GraphStore.upsert_relations(relations)

This guarantees:
- Relationships are stored as [:REL {label: ..., source: ...}] (via GraphStore.upsert_relation)
- Dedupe policy is identical to pipeline (label + source + endpoints)
- Timestamps are identical (GraphStore generates now_iso internally)

Usage:
$ python -m tools.import_triplets --csv data/seed/triplets.csv --source "Seed Import v1"
"""

from __future__ import annotations

import argparse
import csv
import os

from kbdebugger.graph import get_graph
from kbdebugger.types import GraphRelation, EdgeProperties


def normalize(text: str) -> str:
    """Trim and collapse whitespace for consistent graph labels."""
    return " ".join((text or "").strip().split())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import seed triplets into AuraDB using pipeline upsert logic (GraphStore)."
    )
    parser.add_argument(
        "--csv",
        default="data/seed/IEEE-P1522-2004.csv",
        help="Path to seed triplets CSV (semicolon-separated). Default: data/seed/triplets.csv",
    )
    parser.add_argument(
        "--source",
        default="IEEE-P1522-2004.csv",
        help=(
            "Provenance string stored in relationship properties as 'source'. "
            "If omitted, falls back to the --csv path."
        ),
    )
    return parser.parse_args()



def row_to_relation(
    *,
    src: str,
    pred: str,
    dst: str,
    source: str,
) -> GraphRelation:
    """
    Convert a CSV (src, pred, dst) triple into a GraphRelation compatible with GraphStore.upsert_relation().

    Note:
    - We intentionally do NOT set created_at/last_updated_at here.
      GraphStore.upsert_relation() owns timestamps so behavior stays identical to pipeline.
    """
    sentence = f"{src} {pred} {dst}"

    props: EdgeProperties = {
        "sentence": sentence,
        "source": source,          # <-- IMPORTANT: used in dedupe key (label + source)
        # "predicate_text": pred,    # optional but useful for tracing/normalization
        # "original_sentence": sentence,  # since this is seed data, original == synthesized
    }


    relation: GraphRelation = {
        "source": {"label": src},
        "target": {"label": dst},
        "edge": {
            "label": pred,
            "properties": props,
        },
    }
    return relation


def main() -> None:
    args = parse_args()
    csv_path: str = args.csv
    seed_source: str = args.source or csv_path

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    graph = get_graph()

    try:
        relations: list[GraphRelation] = []

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")  # source;relationship;destination

            for i, r in enumerate(reader, start=1):
                src = normalize(r.get("source", ""))
                pred = normalize(r.get("relationship", ""))
                dst = normalize(r.get("destination", ""))

                if not (src and pred and dst):
                    # Skip malformed rows quietly, but you can also print if you prefer
                    continue

                relations.append(
                    row_to_relation(
                        src=src,
                        pred=pred,
                        dst=dst,
                        source=seed_source,
                    )
                )

        if not relations:
            raise RuntimeError(f"No valid rows found in {csv_path}")

        summary = graph.upsert_relations(relations)

        # # Minimal plain output as well (useful in logs)
        # print(
        #     f"[Import] ✅ Done | attempted={summary.attempted} "
        #     f"succeeded={summary.succeeded} failed={summary.failed} "
        #     f"source={seed_source!r}"
        # )

        # if summary.failed > 0:
        #     print("[Import] ❌ Some rows failed. First few errors:")
        #     for err in summary.errors[:10]:
        #         print(f"  - {err}")

    finally:
        graph.close()


if __name__ == "__main__":
    main()
