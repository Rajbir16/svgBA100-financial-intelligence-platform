"""API utility helpers for sanitizing data and JSON serializing."""

import math
from typing import Any, Dict, List


def sanitize_json_value(v: Any) -> Any:
    """Recursively sanitize float NaN and Inf to None for valid JSON serialization."""
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(v, dict):
        return {k: sanitize_json_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [sanitize_json_value(item) for item in v]
    return v


def sanitize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize a list of dictionary records for JSON compliance."""
    return [sanitize_json_value(r) for r in records]

