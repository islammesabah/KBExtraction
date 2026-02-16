from __future__ import annotations

from typing import Callable

ProgressCallback = Callable[[int, int, str], None] 
# current, total, message
