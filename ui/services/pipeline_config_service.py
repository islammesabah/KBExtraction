"""
PipelineConfig service for the Flask UI.

Why this exists
---------------
- The core project already defines `PipelineConfig.from_env()` as the *single*
  authoritative place for runtime configuration.
- The UI should not re-parse environment variables inside routes.
- We create the config once (cached) and reuse it across requests.

Notes
-----
- We assume `.env` is loaded once during app startup (in the app factory),
  not inside request handlers.
"""

from __future__ import annotations

from functools import lru_cache

from kbdebugger.pipeline.config import PipelineConfig


@lru_cache(maxsize=1)
def get_pipeline_config() -> PipelineConfig:
    """
    Return a cached PipelineConfig loaded from environment variables.

    Returns
    -------
    PipelineConfig
        Central runtime config for the pipeline / UI.
    """
    return PipelineConfig.from_env()
