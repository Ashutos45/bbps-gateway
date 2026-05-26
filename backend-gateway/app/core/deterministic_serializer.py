import json
from typing import Any

def canonical_serialize(obj: Any) -> bytes:
    """
    Serializes a Python object to canonical JSON format:
    1. Sorts all dictionary keys recursively.
    2. Removes all extraneous whitespace (separators are strictly ',' and ':').
    3. Encodes the resulting string to UTF-8.
    """
    if obj is None:
        return b""
        
    # Standardize dictionary keys recursively before serialization if not already handled
    # json.dumps handles recursive dictionary key sorting automatically when sort_keys=True
    canonical_str = json.dumps(
        obj, 
        sort_keys=True, 
        separators=(",", ":"), 
        ensure_ascii=False
    )
    return canonical_str.encode("utf-8")
