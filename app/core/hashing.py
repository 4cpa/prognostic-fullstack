import hashlib
import json
from typing import Any

def stable_hash(payload: Any) -> str:
    dumped = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()
