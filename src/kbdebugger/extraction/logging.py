from typing import Any, Sequence
import rich

from kbdebugger.compat.langchain import Document
from kbdebugger.utils.json import write_json
from kbdebugger.utils.time import now_utc_compact
from .types import Qualities, SourceKind, DecomposeMode

def save_chunked_documents_json(
    *, 
    docs: Sequence[Document],
    source_kind: SourceKind,
) -> None:
    """
    Save LangChain Documents to JSON for debugging/demo purposes.

    What we store (per document)
    ----------------------------
    - page_content: the text chunk that will be fed to the Decomposer
    - metadata: provenance fields produced by the loader/chunker

    Notes
    -----
    - This is meant for inspection and reproducibility.
    - It does not attempt to preserve Document objects exactly, only their content.
    """
    created_at = now_utc_compact()
    payload: dict[str, Any] = {
        "num_docs": len(docs),
        "docs": [
            {
                "page_content": getattr(doc, "page_content", ""),
                "metadata": dict(getattr(doc, "metadata", {}) or {}),
            }
            for doc in docs
        ],
        "created_at": created_at,
    }

    path = f"logs/01.1_chunker_output_docs_{source_kind}_{created_at}.json"
    write_json(path, payload)

    rich.print(f"\n[INFO] Wrote chunker output log to {path}")



def save_qualities_json(
        *, 
        qualities: Qualities, 
        meta: dict[str, Any] | None = None,
        mode: DecomposeMode
    ) -> None:
    """
    Save Decomposer output qualities (atomic sentences) to JSON.

    Parameters
    ----------
    qualities:
        The list of atomic sentences returned by the decomposer.

    Output structure
    ----------------
    {
      "num_qualities": N,
      "qualities": [...]
    }
    """
    created_at = now_utc_compact()
    payload: dict[str, Any] = {
        "num_qualities": len(qualities),
        "qualities": list(qualities),
        "created_at": created_at,
    }
    if meta:
        payload["meta"] = meta

    path = f"logs/01.2_decomposer_qualities_{mode}_{created_at}.json"
    write_json(path, payload)

    rich.print(f"\n[INFO] Wrote decomposer qualities log to {path}")