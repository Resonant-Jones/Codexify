from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[2] / "scripts" / "github" / "campaign_control_plane_core.py"
spec = importlib.util.spec_from_file_location("campaign_control_plane", MODULE_PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def body(*, ownership=True, approved=True, privacy=False):
    own = "This change belongs in scripts/github/campaign_control_plane.py" if ownership else ""
    priv = "\nPrivacy sentinel: required" if privacy else ""
    return f"""Parent campaign: #625
## Workflow lane
`architecture-impact`
## Task kind
`implementation`
## Context
Context.{priv}
## Goal
Goal.
## Files
- scripts/github/campaign_control_plane.py
## Ownership
{own}
## Acceptance criteria
- Done.
## Non-goals
- No merge.
## Validation
- pytest -q
## Git commands
`git add scripts/github/campaign_control_plane.py`
`git commit -m \"feat: dry run\"`
## Expected closeout
- Summary of changes
- Files changed
- Git commit hash
- What Axis should add to his KB
## Board metadata
- Lane: architecture-impact
## Source evidence
- docs/example.md
"""


def issue(labels=(m.APPROVAL_LABEL,), text=None, number=626):
    return m.IssuePacket(number, text or body(), labels)


def checks(conclusion="success"):
    return [{"name": n, "status": "completed", "conclusion": conclusion} for n in m.REQUIRED_CHECK_NAMES]


def pr(**overrides):
    value = {"body": "Closes #626", "draft": False, "state": "open", "mergeable_state": "clean", "labels": [{"name": m.MERGE_AUTHORITY_LABEL}]}
    value.update(overrides)
    return value


def evaluate(**kwargs):
    defaults = dict(pr=pr(), referenced_issues=[issue()], checks=checks(), reviews=[], changed_files=[{"filename": "scripts/github/campaign_control_plane.py", "patch": "+safe"}])
    defaults.update(kwargs)
    return m.evaluate_pr(**defaults)


def test_valid_approved_issue_packet(): assert m.evaluate_issue(issue()).state == "eligible_dry_run"
def test_missing_required_section(): assert "issue_packet_invalid" in m.evaluate_issue(issue(text=body().replace("Goal.", ""))).blockers
def test_missing_ownership_line(): assert "issue_packet_invalid" in m.evaluate_issue(issue(text=body(ownership=False))).blockers
def test_unapproved_issue(): assert m.evaluate_issue(issue(labels=())).blockers == ("issue_not_approved",)
def test_correctly_linked_pr(): assert evaluate().state == "eligible_dry_run"
def test_parent_only_link_is_missing_lineage():
    campaign = m.IssuePacket(625, "## Goal\nParent campaign record", ())
    assert m.evaluate_pr(pr=pr(body="Closes #625"), referenced_issues=[campaign], checks=checks(), reviews=[], changed_files=[]).state == "missing_lineage"
def test_draft_pr(): assert "pr_is_draft" in evaluate(pr=pr(draft=True)).blockers
def test_missing_required_check(): assert "required_checks_missing" in evaluate(checks=checks()[:-1]).blockers
def test_failing_required_check(): assert "required_checks_failing" in evaluate(checks=checks("failure")).blockers
def test_requested_changes(): assert "requested_changes_present" in evaluate(reviews=[{"id": 1, "state": "CHANGES_REQUESTED", "user": {"login": "reviewer"}, "submitted_at": "2026-01-01T00:00:00Z"}]).blockers
def test_later_approval_clears_requested_changes(): assert "requested_changes_present" not in evaluate(reviews=[{"id": 1, "state": "CHANGES_REQUESTED", "user": {"login": "r"}, "submitted_at": "2026-01-01T00:00:00Z"}, {"id": 2, "state": "APPROVED", "user": {"login": "r"}, "submitted_at": "2026-01-02T00:00:00Z"}]).blockers
def test_branch_out_of_date(): assert "branch_out_of_date" in evaluate(pr=pr(mergeable_state="behind")).blockers
def test_scope_failure(): assert "scope_validation_failed" in evaluate(changed_files=[{"filename": "unrelated.txt", "patch": "+x"}]).blockers
def test_privacy_failure(): assert "privacy_sentinel_failed" in evaluate(referenced_issues=[issue(text=body(privacy=True))], changed_files=[{"filename": "scripts/github/campaign_control_plane.py", "patch": '+ API_KEY="supersecretvalue"'}]).blockers
def test_missing_merge_authority(): assert "merge_authority_missing" in evaluate(pr=pr(labels=[])).blockers
def test_fully_eligible_dry_run(): assert evaluate().blockers == ()
def test_duplicate_event_decision_id_is_stable():
    ev = evaluate(); args = dict(event_name="pull_request", event_action="synchronize", repository="o/r", workflow_run_id="1", workflow_run_attempt="1", target_kind="pull_request", target_number=7, evaluation=ev, evidence={"head_sha":"abc"})
    assert m.build_receipt(**args)["decision_id"] == m.build_receipt(**{**args, "workflow_run_id":"2"})["decision_id"]
def test_untrusted_issue_content_not_executed():
    text = body().replace("Context.", "Context. $(touch /tmp/pwned) `rm -rf /`")
    assert m.validate_issue_packet(issue(text=text)).valid
    assert not Path("/tmp/pwned").exists()
def test_fork_pr_has_no_special_authority():
    result = evaluate(pr=pr(head={"repo":{"fork":True}}))
    assert result.state == "eligible_dry_run"
def test_title_issue_number_does_not_create_lineage():
    result = m.evaluate_pr(pr={**pr(body=""), "title":"Fix #626"}, referenced_issues=[issue()], checks=checks(), reviews=[], changed_files=[])
    assert result.state == "missing_lineage"
def test_multiple_child_links_are_rejected():
    result = m.evaluate_pr(pr=pr(body="Closes #626\nCloses #627"), referenced_issues=[issue(number=626), issue(number=627)], checks=checks(), reviews=[], changed_files=[])
    assert result.state == "missing_lineage"


def test_workflow_has_no_elevated_permissions_or_pull_request_target():
    workflow = (Path(__file__).parents[2] / ".github" / "workflows" / "campaign-control-plane.yml").read_text()
    assert "pull_request_target" not in workflow
    assert "contents: write" not in workflow
    assert "pull-requests: write" not in workflow
    assert "id-token: write" not in workflow
    assert "persist-credentials: false" in workflow


def test_fork_checkout_falls_back_to_default_branch_expression():
    workflow = (Path(__file__).parents[2] / ".github" / "workflows" / "campaign-control-plane.yml").read_text()
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow
    assert "github.event.repository.default_branch" in workflow


def test_heading_style_lane_and_task_kind_are_accepted():
    validation = m.validate_issue_packet(issue())
    assert validation.workflow_lane == "architecture-impact"
    assert validation.task_kind == "implementation"
    assert validation.valid
