import json
from typing import Union

def canonicalize_json_string(json_str: Union[str, bytes]) -> str:
    """
    Parses a JSON string/bytes, formats it canonically (sorted keys, no spaces),
    and returns the resulting string.
    """
    if not json_str:
        return ""
    
    if isinstance(json_str, bytes):
        json_str = json_str.decode("utf-8")
        
    obj = json.loads(json_str)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def canonicalize_bytes(data: bytes) -> bytes:
    """
    Parses a JSON byte payload, formats it canonically, and returns bytes.
    """
    if not data:
        return b""
    return canonicalize_json_string(data).encode("utf-8")
