"""PHQ-9 and GAD-7 assessment scoring."""

from __future__ import annotations

_INSTRUMENTS: dict[str, tuple[int, list[tuple[int, str]]]] = {
    "phq9": (
        9,
        [
            (4, "minimal"),
            (9, "mild"),
            (14, "moderate"),
            (19, "moderately_severe"),
            (27, "severe"),
        ],
    ),
    "gad7": (
        7,
        [
            (4, "minimal"),
            (9, "mild"),
            (14, "moderate"),
            (21, "severe"),
        ],
    ),
}


def score_assessment(instrument: str, responses: dict[str, int]) -> tuple[int, str]:
    """Score an assessment and return (total_score, severity).

    Args:
        instrument: "phq9" or "gad7"
        responses: {"q1": 0, "q2": 1, ...} with values 0-3

    Returns:
        (total_score, severity_label)

    Raises:
        ValueError: if instrument unknown, questions missing, or scores out of range.
    """
    if instrument not in _INSTRUMENTS:
        raise ValueError(f"Unknown instrument: {instrument}")

    num_questions, thresholds = _INSTRUMENTS[instrument]
    expected_keys = {f"q{i}" for i in range(1, num_questions + 1)}
    missing = expected_keys - set(responses.keys())
    if missing:
        raise ValueError(f"Missing questions: {sorted(missing)}")

    total = 0
    for key in expected_keys:
        val = responses[key]
        if not isinstance(val, int) or val < 0 or val > 3:
            raise ValueError(f"{key} value {val} out of range (0-3)")
        total += val

    severity = thresholds[-1][1]
    for threshold, label in thresholds:
        if total <= threshold:
            severity = label
            break

    return total, severity
