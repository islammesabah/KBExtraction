from __future__ import annotations
import os
from typing import Protocol, Any, Optional, cast
from kbdebugger.compat.langchain import Neo4jGraph
from neo4j.exceptions import Neo4jError
from dotenv import load_dotenv
# load the environment variables
load_dotenv(override=True)

class GraphClient(Protocol):
    def query(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...
    # ... means no implementation here, just a protocol definition
    # We would implement this interface in concrete classes like Neo4jClient.
    # Meaning: any class that implements GraphClient must have a method query(...) with that signature, returning a list[dict[str, Any]]

def connect_graph_client(
    *, # force keyword args for clarity (no positional args)
    url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    auto_env: bool = True,
) -> GraphClient:
    """
    Creates and returns a typed GraphClient. Reads .env if auto_env=True.
    The cast is hidden here, so callers see a precise type.
    """
    if auto_env:
        load_dotenv(override=True)

    neo4j_url = url or os.getenv("NEO4J_URI")
    neo4j_user = username or os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_pass = password or os.getenv("NEO4J_PASSWORD", "")

    if not neo4j_url:
        raise RuntimeError("NEO4J_URI is not set (pass url=... or set env var).")

    base_client = Neo4jGraph(url=neo4j_url, username=neo4j_user, password=neo4j_pass)
    
    # --- Wrap the base client to add error reporting ---
    class SafeNeo4jGraph:
        def __init__(self, inner: Neo4jGraph):
            self.inner = inner

        def query(self, query: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
            try:
                return self.inner.query(query, params or {})
            except Neo4jError as e:
                raise RuntimeError(
                    f"Neo4j query failed!\nError: {e.__class__.__name__}: {e}\nQuery:\n{query}\nParams:\n{params}"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"Unexpected error during Neo4j query:\n{e}\nQuery:\n{query}\nParams:\n{params}"
                ) from e

    return cast(GraphClient, SafeNeo4jGraph(base_client))
