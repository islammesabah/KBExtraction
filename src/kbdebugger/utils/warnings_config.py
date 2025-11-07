import os
import warnings

def install_warning_filters() -> None:
    """
    Install project-wide warning filters.
    Toggle with SUPPRESS_WARNINGS=0 to see everything.
    """
    if os.getenv("SUPPRESS_WARNINGS", "1") != "1":
        return  # don't suppress if user wants full verbosity

    # --- LangChain deprecations (Neo4jGraph from community package) ---
    try:
        from langchain_core._api.deprecation import LangChainDeprecationWarning
        warnings.filterwarnings(
            "ignore",
            category=LangChainDeprecationWarning,
            message=r".*Neo4jGraph.*was deprecated.*",
        )
    except Exception:
        # if import path changes in future versions, don't crash
        pass

    # --- Other warnings can be added here as needed ---
    # e.g., warnings.filterwarnings("ignore", category=SomeOtherWarning, message=r".*some pattern.*")
