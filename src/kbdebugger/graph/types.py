from dataclasses import dataclass
from typing import List


@dataclass(frozen=True, slots=True)
class BatchUpsertSummary:
    """
    Summary of a batch upsert operation into Neo4j.

    Attributes
    ----------
    attempted:
        Number of relations provided to the batch upsert method.

    succeeded:
        Number of relations that were successfully upserted.

    failed:
        Number of relations that failed to upsert due to an exception.

    errors:
        Human-readable error messages for each failed relation (best-effort).
        Intended for logs and debugging, not for programmatic matching.
    """
    attempted: int
    succeeded: int
    failed: int
    errors: List[str]
