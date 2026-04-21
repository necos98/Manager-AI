import pytest

from app.services.terminal_condition import evaluate_condition, UnknownConditionError


def test_eq_true():
    assert evaluate_condition(
        "$issue_status == Accepted", {"issue_status": "Accepted"}
    ) is True


def test_eq_false():
    assert evaluate_condition(
        "$issue_status == Accepted", {"issue_status": "New"}
    ) is False


def test_neq_true():
    assert evaluate_condition(
        "$issue_status != Canceled", {"issue_status": "New"}
    ) is True


def test_neq_false():
    assert evaluate_condition(
        "$issue_status != Canceled", {"issue_status": "Canceled"}
    ) is False


def test_empty_condition_passes():
    assert evaluate_condition("", {}) is True
    assert evaluate_condition(None, {}) is True
    assert evaluate_condition("   ", {}) is True


def test_unknown_variable_is_false():
    assert evaluate_condition("$nope == x", {}) is False


def test_strips_matched_quotes():
    assert evaluate_condition(
        '$issue_status == "Accepted"', {"issue_status": "Accepted"}
    ) is True
    assert evaluate_condition(
        "$issue_status == 'Accepted'", {"issue_status": "Accepted"}
    ) is True


def test_unknown_operator_raises():
    with pytest.raises(UnknownConditionError):
        evaluate_condition(
            "$issue_status matches Accepted", {"issue_status": "Accepted"}
        )


def test_missing_variable_prefix_raises():
    with pytest.raises(UnknownConditionError):
        evaluate_condition("issue_status == Accepted", {"issue_status": "Accepted"})


def test_multiple_variables():
    assert evaluate_condition(
        "$priority == high",
        {"issue_status": "New", "priority": "high"},
    ) is True
