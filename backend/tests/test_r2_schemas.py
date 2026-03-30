import pytest
from pydantic import ValidationError

from app.schemas.issue import IssueCreate, IssueCompleteBody, IssueUpdate


def test_issue_create_description_too_long():
    with pytest.raises(ValidationError):
        IssueCreate(description="x" * 50_001)


def test_issue_create_description_at_limit():
    obj = IssueCreate(description="x" * 50_000)
    assert len(obj.description) == 50_000


def test_issue_complete_recap_too_long():
    with pytest.raises(ValidationError):
        IssueCompleteBody(recap="x" * 50_001)


def test_issue_complete_recap_at_limit():
    obj = IssueCompleteBody(recap="x" * 50_000)
    assert len(obj.recap) == 50_000


def test_issue_update_spec_too_long():
    with pytest.raises(ValidationError):
        IssueUpdate(spec="x" * 500_001)


def test_issue_update_spec_at_limit():
    obj = IssueUpdate(spec="x" * 500_000)
    assert len(obj.spec) == 500_000


def test_issue_update_plan_too_long():
    with pytest.raises(ValidationError):
        IssueUpdate(plan="x" * 500_001)


def test_issue_update_plan_at_limit():
    obj = IssueUpdate(plan="x" * 500_000)
    assert len(obj.plan) == 500_000
