import sys
from pathlib import Path

# Ensure the package in this repository is importable without installation.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
