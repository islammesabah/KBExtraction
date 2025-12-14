from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, cast
from typing_extensions import LiteralString

from dotenv import load_dotenv
import rich

from neo4j import GraphDatabase, Driver, Query
from neo4j.exceptions import Neo4jError

from kbdebugger.types import GraphRelation, EdgeProperties
from .utils import rows_to_graph_relations


# Load env vars once here
load_dotenv(override=True)

@dataclass
class GraphStore:
    """
    Central access point to the knowledge graph.

    - Handles connecting to Neo4j
    - Exposes:
        - `query(...)` for arbitrary Cypher
        - `upsert_relation(...)` for writing extracted relations
    """
    # inner: Neo4jGraph
    driver: Driver

    # ---------- construction / connection ----------
    @classmethod
    def connect(
        cls,
        *,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auto_env: bool = True,
        verbose: bool = True,
    ) -> "GraphStore":
        """
        Build a GraphStore from environment variables (or explicit args).

        Env vars:
            - NEO4J_URI
            - NEO4J_USERNAME (default "neo4j")
            - NEO4J_PASSWORD (default "")
        """
        if auto_env:
            load_dotenv(override=True)

        neo4j_uri = uri or os.getenv("NEO4J_URI")
        neo4j_user = username or os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_pass = password or os.getenv("NEO4J_PASSWORD", "")

        if not neo4j_uri:
            raise RuntimeError("NEO4J_URI is not set (pass uri=... or set env var).")

        # inner = Neo4jGraph(url=neo4j_uri, username=neo4j_user, password=neo4j_pass)
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))

        if verbose:
            rich.print(
                f"[kbdebugger] Connected to Neo4j at {neo4j_uri!r} "
                f"as user {neo4j_user!r}"
            )

        # return cls(inner=inner)
        return cls(driver=driver)


    def close(self) -> None:
        self.driver.close()


    # ---------- basic query API ----------
    def query(
        self,
        cypher: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run a Cypher query with consistent error handling.

        This is the *only* low-level escape hatch other code should use.
        """
        print("GraphStore backend:", type(self.driver), type(self))
        try:
            with self.driver.session() as session:
                cypher_as_literal_str = cast(LiteralString, cypher)
                # result = session.run(Query(cypher), params or {})
                result = session.run(cypher_as_literal_str, params or {})
                return [record.data() for record in result]
        except Neo4jError as e:
            message = "Neo4j query failed!\n" \
                f"Error: {e.__class__.__name__}: {e}\n" \
                f"Query:\n{cypher}\n" \
                f"Params:\n{params}"
            
            rich.print(
                f"[bold red]{message}[/bold red]\n"
            )
            raise RuntimeError(message) from e
        except Exception as e:
            raise RuntimeError(
                "Unexpected error during Neo4j query:\n"
                f"{e}\nQuery:\n{cypher}\nParams:\n{params}"
            ) from e


    def query_relations(
        self,
        cypher: str,
        params: dict[str, Any] | None = None,
        *,
        source_key: str = "source",
        target_key: str = "target",
        predicate_key: str = "predicate",
        props_key: str = "props",
    ) -> list[GraphRelation]:
        """
        Run a Cypher query that returns (source, target, predicate, props) columns
        and coerce it to List[GraphRelation].
        """
        rows = self.query(cypher, params=params or {})
        return rows_to_graph_relations(
            rows,
            source_key=source_key,
            target_key=target_key,
            predicate_key=predicate_key,
            props_key=props_key,
        )


    # ---------- high-level write API ----------
    def upsert_relation(self, relation: GraphRelation) -> list[dict[str, Any]]:
        """
        Insert or update a single GraphRelation into Neo4j.

        - Nodes are always `(:Node {label: ...})`
        - Relationships are always `[:REL {label: ..., ...}]`
        - Dedupe is based on (`source_label`, `target_label`, `rel.label`, `edge.properties['source']`)
            - i.e., we assume that the same relation from the same source text is the same fact.

        Example relation:
        ```
            relation = {
                'source': {
                    'label': 'Monitoring'
                },
                'target': {
                    'label': 'KI system'
                },
                'edge': {
                    'label': 'is performed during operation of',
                    'properties': {
                        'sentence': 'Monitoring is performed during operation of KI system',
                        'source': '20241015_MISSION_KI_Glossar_v1.0 en.pdf',
                        'page_number': 1,
                        'start_index': 0
                    }
                },
            }
        ```
        """

        src_label = relation["source"]["label"]
        tgt_label = relation["target"]["label"]
        rel_label = relation["edge"]["label"]
        props_all = relation["edge"]["properties"]

        # Key used to *match* existing relationships (dedupe policy)
        rel_key_props: EdgeProperties = {
            "label": rel_label,
            "source": props_all.get("source", ""),
            # Add more fields here if we want stricter deduplication
        }
        # ⚠️ remember: the rel_key_props are the props of the relationship used to find existing rels!
        # so choose them carefully to avoid over- or under-merging.

        # Why this is safer
        # - We won't create a new rel just because page_number or some metadata changed.
        # - We still persist all the rich properties on first create, and can update on matches.

        now_iso = datetime.now(timezone.utc).isoformat()

        # Properties set only when a relationship is first created
        on_create_props: EdgeProperties = {
            **props_all,
            "created_at": now_iso,
        }

        # Properties updated whenever we re-encounter the same relationship
        on_match_props = {
            "last_updated_at": now_iso,
        }

        """
        apoc.merge.relationship is a Neo4j APOC procedure used to dynamically merge or create a relationship between two nodes, which either exists or is created based on the provided parameters. 
        It handles dynamic relationship types and properties for creation or matching, and its signature is apoc.merge.relationship(
            startNode, 
            relType,        # e.g., "REL"
            relKeyProps,    # properties used to identify existing relationships
            onCREATEProps,  # properties set only when a new relationship is created
            endNode, 
            onMatchProps    # properties updated when a relationship already exists
        ). 
        This is useful for building Cypher queries where the relationship details are provided as parameters, for example, when unwinding a list of rows.
        """
        
        # About {} vs {{}}
        # - In a plain triple-quoted Python string (""" ... """), {} is just literal braces — fine.
        # - In an f-string (f""" ... """), {} is interpolation. To emit literal braces, we must escape as {{}}.
        # So:
        # - If we keep it as a plain string: """ ... {} ... """ is OK.
        # - If we switch to f""" ... """: change to {{}}.

        cypher = """
        MERGE (s:Node {label: $source_label})
        ON CREATE SET s.created_at = datetime()
        SET s.last_updated_at = datetime(),
            s.created_at = coalesce(s.created_at, datetime())

        MERGE (t:Node {label: $target_label})
        ON CREATE SET t.created_at = datetime()
        SET t.last_updated_at = datetime(),
            t.created_at = coalesce(t.created_at, datetime())

        WITH s, t
        CALL apoc.merge.relationship(
            s,
            $rel_type,
            $rel_key_props,
            $on_create,
            t,
            $on_match
        ) YIELD rel

        // ensure temporal props exist on the rel too
        SET rel.created_at    = coalesce(rel.created_at, datetime()),
            rel.last_updated_at = datetime()

        RETURN s, t, rel
        """

        return self.query(
            cypher,
            params={
                "source_label": src_label,
                "target_label": tgt_label,
                "rel_type": "REL", # always 'REL' as the relationship type; actual label is in properties
                "rel_key_props": rel_key_props,
                "on_create": on_create_props, # set only on create of the relationship
                "on_match": on_match_props, # set only on match (update) of the relationship
            },
        )
