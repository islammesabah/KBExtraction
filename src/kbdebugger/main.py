from __future__ import annotations

from kbdebugger.pipeline.config import PipelineConfig
from kbdebugger.pipeline.run import run_pipeline


def main() -> None:
    cfg = PipelineConfig.from_env()
    run_pipeline(cfg)


if __name__ == "__main__":
    main()
