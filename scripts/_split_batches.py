"""Split script_input_2.json and script_input_4.json each into 2 halves.

Outputs:
  script_input_2a.json (first 50)
  script_input_2b.json (last 50)
  script_input_4a.json (first 50)
  script_input_4b.json (last 50)
"""
import json
from pathlib import Path

EXPORTS = Path(__file__).parent.parent / "data" / "exports"

for n in (2, 4):
    src = EXPORTS / f"script_input_{n}.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    half = len(data) // 2
    (EXPORTS / f"script_input_{n}a.json").write_text(json.dumps(data[:half], indent=2, ensure_ascii=False), encoding="utf-8")
    (EXPORTS / f"script_input_{n}b.json").write_text(json.dumps(data[half:], indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  split {src.name}: {half} + {len(data) - half}")
