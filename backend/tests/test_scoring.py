"""Tests for PHQ-9 and GAD-7 assessment scoring."""

from __future__ import annotations

import pytest

from app.services.scoring import score_assessment


def test_phq9_minimal() -> None:
    responses = {f"q{i}": 0 for i in range(1, 10)}
    total, severity = score_assessment("phq9", responses)
    assert total == 0
    assert severity == "minimal"


def test_phq9_mild() -> None:
    responses = {f"q{i}": 0 for i in range(1, 10)}
    responses["q1"] = 3
    responses["q2"] = 2
    responses["q3"] = 2
    total, severity = score_assessment("phq9", responses)
    assert total == 7
    assert severity == "mild"


def test_phq9_moderate() -> None:
    responses = {f"q{i}": 1 for i in range(1, 10)}
    responses["q1"] = 3
    responses["q2"] = 2
    total, severity = score_assessment("phq9", responses)
    assert total == 12
    assert severity == "moderate"


def test_phq9_moderately_severe() -> None:
    responses = {f"q{i}": 2 for i in range(1, 10)}
    responses["q9"] = 1
    total, severity = score_assessment("phq9", responses)
    assert total == 17
    assert severity == "moderately_severe"


def test_phq9_severe() -> None:
    responses = {f"q{i}": 3 for i in range(1, 10)}
    total, severity = score_assessment("phq9", responses)
    assert total == 27
    assert severity == "severe"


def test_gad7_minimal() -> None:
    responses = {f"q{i}": 0 for i in range(1, 8)}
    total, severity = score_assessment("gad7", responses)
    assert total == 0
    assert severity == "minimal"


def test_gad7_mild() -> None:
    responses = {f"q{i}": 1 for i in range(1, 8)}
    total, severity = score_assessment("gad7", responses)
    assert total == 7
    assert severity == "mild"


def test_gad7_moderate() -> None:
    responses = {f"q{i}": 2 for i in range(1, 8)}
    total, severity = score_assessment("gad7", responses)
    assert total == 14
    assert severity == "moderate"


def test_gad7_severe() -> None:
    responses = {f"q{i}": 3 for i in range(1, 8)}
    total, severity = score_assessment("gad7", responses)
    assert total == 21
    assert severity == "severe"


def test_unknown_instrument_raises() -> None:
    with pytest.raises(ValueError, match="Unknown instrument"):
        score_assessment("unknown", {"q1": 0})


def test_missing_question_raises() -> None:
    responses = {f"q{i}": 0 for i in range(1, 8)}
    with pytest.raises(ValueError, match="Missing"):
        score_assessment("phq9", responses)


def test_invalid_score_raises() -> None:
    responses = {f"q{i}": 0 for i in range(1, 10)}
    responses["q1"] = 5
    with pytest.raises(ValueError, match="out of range"):
        score_assessment("phq9", responses)
