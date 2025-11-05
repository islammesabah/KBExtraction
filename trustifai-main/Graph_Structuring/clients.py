from __future__ import annotations
import os
from typing import Protocol, Any, Optional, cast
from langchain_community.graphs import Neo4jGraph
from dotenv import load_dotenv
# load the environment variables
load_dotenv(override=True)
# graph/clients.py
from typing import Protocol, Any

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

    client = Neo4jGraph(url=neo4j_url, username=neo4j_user, password=neo4j_pass)
    return cast(GraphClient, client)
