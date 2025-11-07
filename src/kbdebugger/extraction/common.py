from typing import Callable

Qualities = list[str]  # e.g., ["Transparency is a property of KI system.", ...]
TextDecomposer = Callable[[str], Qualities]
