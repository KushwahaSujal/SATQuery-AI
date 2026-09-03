import sys
from pathlib import Path

_satquery_ai_root = Path(__file__).resolve().parent.parent
if str(_satquery_ai_root) not in sys.path:
    sys.path.insert(0, str(_satquery_ai_root))
