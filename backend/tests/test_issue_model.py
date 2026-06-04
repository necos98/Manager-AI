from app.models.issue import IssueStatus


def test_declined_not_in_status_enum():
    statuses = [s.value for s in IssueStatus]
    assert "Declined" not in statuses
