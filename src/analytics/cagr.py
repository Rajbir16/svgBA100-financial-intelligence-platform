"""CAGR calculations with explicit sign-state classifications."""

from typing import Dict, Optional, Tuple


def classify_cagr(start: Optional[float], end: Optional[float]) -> str:
    if start is None or end is None:
        return "INSUFFICIENT"
    if start == 0:
        return "ZERO_BASE"
    if start > 0 and end > 0:
        return "NORMAL"
    if start > 0 and end <= 0:
        return "DECLINE_TO_LOSS"
    if start < 0 and end > 0:
        return "TURNAROUND"
    return "BOTH_NEGATIVE"


def calculate_cagr(start: Optional[float], end: Optional[float], years: int) -> Tuple[Optional[float], str]:
    flag = classify_cagr(start, end)
    if years <= 0 or flag != "NORMAL":
        return None, flag
    return ((end / start) ** (1 / years) - 1) * 100, flag


def cagr_for_series(values: Dict[int, Optional[float]], end_year: int, years: int) -> Tuple[Optional[float], str]:
    start = values.get(end_year - years)
    end = values.get(end_year)
    if start is None or end is None:
        return None, "INSUFFICIENT"
    return calculate_cagr(start, end, years)