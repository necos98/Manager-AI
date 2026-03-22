from app.models.issue import IssueStatus, VALID_TRANSITIONS


def test_declined_not_in_status_enum():
    statuses = [s.value for s in IssueStatus]
    assert "Declined" not in statuses


def test_valid_transitions_include_new_to_reasoning():
    assert (IssueStatus.NEW, IssueStatus.REASONING) in VALID_TRANSITIONS


def test_valid_transitions_do_not_include_declined():
    for src, dst in VALID_TRANSITIONS:
        assert src != "Declined" and dst != "Declined"


def test_all_expected_transitions_present():
    expected = {
        (IssueStatus.NEW, IssueStatus.REASONING),
        (IssueStatus.REASONING, IssueStatus.PLANNED),
        (IssueStatus.PLANNED, IssueStatus.ACCEPTED),
        (IssueStatus.ACCEPTED, IssueStatus.FINISHED),
    }
    assert VALID_TRANSITIONS == expected
