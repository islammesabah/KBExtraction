from __future__ import annotations
from typing import Optional

from .store import GraphStore

__all__ = ["get_graph"]

# Internal singleton-ish instance
_graph_instance: Optional[GraphStore] = None

def get_graph() -> GraphStore:
    """
    Return the global GraphStore instance.

    Lazily connects on first call, then reuses that instance.
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = GraphStore.connect()
    return _graph_instance


def set_graph_for_testing(store: GraphStore) -> None:
    """
    Override the global graph instance (e.g., in tests or notebooks).
    """
    global _graph_instance
    _graph_instance = store
