"""Put skills/_shared/ onto sys.path so `import eml_core` works from anywhere."""

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2]  # skills/_shared/
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
