from conveyor.core.governance import (
    needs_plan_approval,
    needs_merge_approval,
    auto_merge_allowed,
)
from conveyor.config import default_config, ConveyorConfig
from conveyor.tracking.models import Issue, RiskLevel


def _make_issue(risk: RiskLevel) -> Issue:
    return Issue(
        id="ISS-001",
        intent="INT-001",
        title="Test issue",
        agent="backend",
        branch="conveyor/iss-001-test",
        depends_on=[],
        risk=risk,
    )


def test_low_risk_auto_merges():
    cfg = default_config()
    issue = _make_issue(RiskLevel.LOW)
    assert auto_merge_allowed(issue, cfg) is True
    assert needs_plan_approval(issue, cfg) is False
    assert needs_merge_approval(issue, cfg) is False


def test_medium_risk_needs_merge_approval():
    cfg = default_config()
    issue = _make_issue(RiskLevel.MEDIUM)
    assert auto_merge_allowed(issue, cfg) is False
    assert needs_plan_approval(issue, cfg) is False
    assert needs_merge_approval(issue, cfg) is True


def test_high_risk_needs_plan_and_merge_approval():
    cfg = default_config()
    issue = _make_issue(RiskLevel.HIGH)
    assert auto_merge_allowed(issue, cfg) is False
    assert needs_plan_approval(issue, cfg) is True
    assert needs_merge_approval(issue, cfg) is True


def test_config_overrides():
    cfg = default_config()
    cfg.auto_merge_low_risk = False
    issue = _make_issue(RiskLevel.LOW)
    assert auto_merge_allowed(issue, cfg) is False
    assert needs_merge_approval(issue, cfg) is True
