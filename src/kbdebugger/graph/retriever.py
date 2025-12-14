from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Sequence, TypedDict

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from kbdebugger.graph import get_graph
from kbdebugger.graph.utils import rows_to_graph_relations
from kbdebugger.types import GraphRelation, EdgePropertyKey
from .utils import normalize_text

MatchPattern = Literal["source_label", "target_label", "rel_props"]

class RetrievedRelation(TypedDict):
    relation: GraphRelation
    match_pattern: MatchPattern

@dataclass
class KnowledgeGraphRetriever:
    """
    Keyword-guided KG retrieval.

    MVP: returns 1-hop 'path fragments' (edges) as normalized GraphRelation objects.
    """
    limit_per_pattern: int = 50
    console: Console = field(default_factory=Console) # console is a member so we can inject a test console or reuse a global one.

    def retrieve(
        self,
        keyword: str,
        *,
        limit_per_pattern: Optional[int] = None,
        # include_match_pattern: bool = True,
    ) -> list[RetrievedRelation]:
        kw = normalize_text(keyword)
        limit = int(limit_per_pattern or self.limit_per_pattern)

        graph = get_graph()

        results: list[RetrievedRelation] = []

        # --- Pattern 1: keyword in source node label ---
        rows = graph.query_relations(
            """
            MATCH (n:Node)-[r:REL]->(m:Node)
            WHERE toLower(n.label) CONTAINS $keyword
            RETURN
              n.label AS source,
              m.label AS target,
              coalesce(r.type, r.label, 'REL') AS predicate,
              properties(r) AS props,

              elementId(n) AS source_id,
              elementId(m) AS target_id,
              elementId(r) AS rel_id
            LIMIT $limit
            """,
            {"keyword": kw, "limit": limit},
        )
        rels = rows_to_graph_relations(rows)
        results.extend({"relation": rel, "match_pattern": "source_label"} for rel in rels)

        # --- Pattern 2: keyword in target node label ---
        rows = graph.query(
            """
            MATCH (n:Node)-[r:REL]->(m:Node)
            WHERE toLower(m.label) CONTAINS $keyword
            RETURN
              n.label AS source,
              m.label AS target,
              coalesce(r.type, r.label, 'REL') AS predicate,
              properties(r) AS props,

              elementId(n) AS source_id,
              elementId(m) AS target_id,
              elementId(r) AS rel_id
            LIMIT $limit
            """,
            {"keyword": kw, "limit": limit},
        )
        rels = rows_to_graph_relations(rows)
        results.extend({"relation": rel, "match_pattern": "target_label"} for rel in rels)

        # --- Pattern 3: keyword in relationship "semantic" fields ---
        # We avoid fancy APOC here; just check the usual fields you write.
        rows = graph.query(
            """
            MATCH (n:Node)-[r:REL]->(m:Node)
            WHERE
                toLower(coalesce(r.type, ""))              CONTAINS $keyword OR
                toLower(coalesce(r.label, ""))             CONTAINS $keyword OR
                toLower(coalesce(r.sentence, ""))          CONTAINS $keyword OR
                toLower(coalesce(r.original_sentence, "")) CONTAINS $keyword OR
                toLower(coalesce(r.source, ""))            CONTAINS $keyword
            RETURN
                n.label AS source,
                m.label AS target,
                coalesce(r.type, r.label, 'REL') AS predicate,
                properties(r) AS props,

                elementId(n) AS source_id,
                elementId(m) AS target_id,
                elementId(r) AS rel_id
            LIMIT $limit
            """,
            {"keyword": kw, "limit": limit},
        )
        rels = rows_to_graph_relations(rows)
        results.extend({"relation": rel, "match_pattern": "rel_props"} for rel in rels)

        # Optional: dedupe identical relations across patterns
        # (same source/target/predicate + same sentence/source if you want)
        results = self._dedupe(results)

        return results
        # if include_match_pattern:
        #     return results
        # return [r["relation"] for r in results]

    @staticmethod
    def _dedupe(items: list[RetrievedRelation]) -> list[RetrievedRelation]:
        seen: set[tuple[str, str, str, str]] = set()
        out: list[RetrievedRelation] = []

        for item in items:
            rel = item["relation"]
            props = rel["edge"]["properties"]
            sentence = str(props.get("sentence", ""))  # good lightweight key
            key = (rel["source"]["label"], rel["target"]["label"], rel["edge"]["label"], sentence)

            if key in seen:
                continue
            seen.add(key)
            out.append(item)

        return out


    def pretty_print(
        self,
        hits: Sequence[RetrievedRelation],
        *,
        title: str = "Knowledge Graph Retrieval Results",
        show_props_keys: Optional[Sequence[EdgePropertyKey]] = None,
    ) -> None:
        """
        Pretty-print RetrievedRelation results using rich.

        - hits: output of retrieve(..., include_match_pattern=True)
        - show_props_keys: if set, prints only these keys from edge.properties (in addition to sentence/source/page)
        """
        if not hits:
            self.console.print("[bold yellow]No matching relations found.[/bold yellow]")
            return

        if not show_props_keys:
            show_props_keys = [
                "created_at", 
                "last_updated_at",
                "original_sentence",
            ]

        self.console.rule(f"[bold cyan]{title}[/bold cyan]")

        for i, hit in enumerate(hits, start=1):
            rel = hit["relation"]
            pattern = hit["match_pattern"]

            src = rel["source"]["label"]
            tgt = rel["target"]["label"]
            pred = rel["edge"]["label"]
            props = rel["edge"]["properties"]

            sentence = props.get("sentence")
            source_doc = props.get("source")
            page = props.get("page_number")

            header = Text()
            header.append(f"[{i}] ", style="bold cyan")
            header.append(f"{src} ", style="bold green")
            header.append("── ", style="dim")
            header.append(pred, style="bold magenta")
            header.append(" ──> ", style="dim")
            header.append(tgt, style="bold green")

            body: list[str] = [f"[bold]Matched via:[/bold] {pattern}"]

            if sentence:
                body.append(f"[bold]Sentence:[/bold] {sentence}")

            if source_doc:
                meta = f"{source_doc}"
                if page is not None:
                    meta += f", page {page}"
                body.append(f"[bold]Source:[/bold] {meta}")

            if show_props_keys:
                for k in show_props_keys:
                    if k in props and props[k] is not None: # type: ignore
                        body.append(f"[bold]{k}:[/bold] {props[k]}") # type: ignore

            self.console.print(
                Panel(
                    "\n".join(body),
                    title=header,
                    border_style="cyan",
                    padding=(1, 2),
                )
            )

