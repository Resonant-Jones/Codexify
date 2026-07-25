"""Pure evaluator for the Codexify campaign control-plane dry run."""
from __future__ import annotations
import datetime as dt, fnmatch, hashlib, json, re
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "campaign_control_plane_receipt.v1"
APPROVAL_LABEL = "ready-for-agent"
MERGE_AUTHORITY_LABEL = "merge-authorized"
PRIVACY_REQUIRED_MARKER = "privacy sentinel: required"
STATES = frozenset({"ineligible", "eligible_dry_run", "blocked", "invalid_packet", "missing_lineage"})
BLOCKER_CODES = frozenset({"issue_not_approved", "issue_packet_invalid", "pr_not_linked_to_issue", "pr_is_draft", "pr_is_closed", "required_checks_missing", "required_checks_failing", "requested_changes_present", "branch_out_of_date", "scope_validation_failed", "privacy_sentinel_failed", "merge_authority_missing", "unsupported_event", "api_error"})
ALLOWED_LANES = frozenset({"standard", "architecture-impact", "proof", "docs", "marketing", "board-hygiene"})
REQUIRED_SECTIONS = ("context", "goal", "files", "acceptance criteria", "non-goals", "validation", "expected closeout", "board metadata", "source evidence")
REQUIRED_CHECK_NAMES = ("Detect Changed Areas", "Backend Tests (Python 3.11)", "alembic-config-sanity", "Frontend Quality", "Migration Contract (Container)")
SUCCESS_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})
SECRET_PATTERNS = (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), re.compile(r"(?i)\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"), re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"))
HEAD_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)
PARENT_RE = re.compile(r"(?im)^\s*Parent campaign:\s*#(\d+)\s*$")
LANE_RE = re.compile(r"(?im)^\s*(?:Workflow lane|Lane):\s*`?([a-z-]+)`?\s*$")
TASK_RE = re.compile(r"(?im)^\s*Task kind:\s*`?([a-z-]+)`?\s*$")
OWN_RE = re.compile(r"(?im)^\s*This change belongs in\s+(.+?)\s*$")
ADD_RE = re.compile(r"(?im)`?git add\s+[^\n`]+`?")
COMMIT_RE = re.compile(r"(?im)`?git commit\s+-m\s+['\"][^'\"]+['\"]`?")
CLOSE_RE = re.compile(r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+(?:[\w.-]+/[\w.-]+)?#(\d+)")
MARKER_RE = re.compile(r"(?im)^\s*(?:Codexify-Child-Issue|Implements-Issue):\s*#(\d+)\s*$")

@dataclass(frozen=True)
class IssuePacket:
    number: int; body: str; labels: tuple[str, ...]; title: str = ""
@dataclass(frozen=True)
class IssueValidation:
    valid: bool; approved: bool; errors: tuple[str, ...]; parent_campaign: int | None
    workflow_lane: str | None; task_kind: str | None; allowed_files: tuple[str, ...]; privacy_required: bool
@dataclass(frozen=True)
class Evaluation:
    state: str; blockers: tuple[str, ...]; details: tuple[str, ...]; linked_child_issue: int | None
    parent_campaign_issue: int | None; issue_validation: IssueValidation | None

def labels(items: Any) -> tuple[str, ...]:
    out=[]
    for item in items or ():
        name=item if isinstance(item,str) else item.get("name") if isinstance(item,Mapping) else None
        if isinstance(name,str): out.append(name)
    return tuple(sorted(set(out)))

def sections(body: str) -> dict[str,str]:
    hits=list(HEAD_RE.finditer(body or "")); out={}
    for i,hit in enumerate(hits):
        name=re.sub(r"\s+"," ",re.sub(r"[`*_]","",hit.group(1)).strip().lower()).rstrip(":")
        end=hits[i+1].start() if i+1<len(hits) else len(body); out[name]=body[hit.end():end].strip()
    return out

def section(parts: Mapping[str,str], name: str) -> str:
    name=name.lower(); return next((v for k,v in parts.items() if k==name or k.startswith(name+" ") or name in k),"")

def field(body: str, parts: Mapping[str,str], inline: re.Pattern[str], heading: str) -> str | None:
    match=inline.search(body)
    if match: return match.group(1).lower()
    value=section(parts,heading).strip(); return value.splitlines()[0].strip("` ").lower() if value else None

def file_specs(body: str) -> tuple[str,...]:
    out=[]
    for raw in section(sections(body),"files").splitlines():
        if not raw.strip().startswith("-"): continue
        value=raw.strip()[1:].strip()
        if value.endswith("(new)"): value=value[:-5].strip()
        value=value.strip("`")
        value=value.replace("<next-number>","*").replace("<actual-number>","*")
        if value and not value.lower().startswith("report every"): out.append(value)
    return tuple(dict.fromkeys(out))

def validate_issue_packet(issue: IssuePacket) -> IssueValidation:
    body=issue.body or ""; parts=sections(body); errors=[]
    found=PARENT_RE.search(body); parent=int(found.group(1)) if found else None
    if parent is None: errors.append("missing_parent_campaign")
    lane=field(body,parts,LANE_RE,"workflow lane")
    if lane not in ALLOWED_LANES: errors.append("missing_or_invalid_workflow_lane")
    task=field(body,parts,TASK_RE,"task kind")
    if not task: errors.append("missing_task_kind")
    for name in REQUIRED_SECTIONS:
        if not section(parts,name): errors.append("missing_section:"+name)
    if not OWN_RE.search(body): errors.append("missing_ownership_line")
    files=file_specs(body)
    if not files: errors.append("missing_explicit_files")
    if not ADD_RE.search(body): errors.append("missing_narrow_git_add")
    if not COMMIT_RE.search(body): errors.append("missing_git_commit")
    closeout=section(parts,"expected closeout").lower()
    for item in ("summary of changes","files changed","git commit hash","what axis should add"):
        if item not in closeout: errors.append("missing_closeout_field:"+item.replace(" ","_"))
    return IssueValidation(not errors,APPROVAL_LABEL in issue.labels,tuple(sorted(set(errors))),parent,lane,task,files,PRIVACY_REQUIRED_MARKER in body.lower())

def parse_linked_issue_numbers(body: str) -> tuple[int,...]:
    return tuple(sorted({*(int(x) for x in CLOSE_RE.findall(body or "")),*(int(x) for x in MARKER_RE.findall(body or ""))}))

def allowed(path: str, specs: Sequence[str]) -> bool:
    path=path.lstrip("./")
    for raw in specs:
        spec=raw.lstrip("./")
        if (spec.endswith("/") and path.startswith(spec)) or path==spec or (any(c in spec for c in "*?[") and fnmatch.fnmatch(path,spec)): return True
    return False

def validate_scope(files: Sequence[Mapping[str,Any]], specs: Sequence[str]):
    bad=tuple(sorted(str(f["filename"]) for f in files if f.get("filename") and not allowed(str(f["filename"]),specs))); return not bad,bad

def validate_privacy(files: Sequence[Mapping[str,Any]], required: bool):
    if not required: return True,()
    findings=[]
    for item in files:
        path,patch=str(item.get("filename","")),item.get("patch")
        if patch is None: findings.append("unscannable:"+path)
        elif any(p.search(str(patch)) for p in SECRET_PATTERNS): findings.append("secret_pattern:"+path)
    return not findings,tuple(sorted(findings))

def active_requested_changes(reviews: Sequence[Mapping[str,Any]]) -> bool:
    latest={}
    for item in reviews:
        user=item.get("user") or {}; login=str(user.get("login") or item.get("user_login") or "")
        if not login: continue
        candidate=(str(item.get("submitted_at") or ""),int(item.get("id") or 0),str(item.get("state") or "").upper())
        if login not in latest or candidate[:2]>=latest[login][:2]: latest[login]=candidate
    return any(x[2]=="CHANGES_REQUESTED" for x in latest.values())

def evaluate_checks(checks: Sequence[Mapping[str,Any]], required: Sequence[str]=REQUIRED_CHECK_NAMES):
    by_name={str(x.get("name") or x.get("context") or ""):x for x in checks}; missing=tuple(x for x in required if x not in by_name); failing=[]
    for name in required:
        item=by_name.get(name)
        if not item: continue
        if str(item.get("status") or "completed").lower()!="completed" or str(item.get("conclusion") or item.get("state") or "").lower() not in SUCCESS_CONCLUSIONS: failing.append(name)
    return missing,tuple(failing)

def evaluate_issue(issue: IssuePacket) -> Evaluation:
    v=validate_issue_packet(issue)
    if not v.valid: return Evaluation("invalid_packet",("issue_packet_invalid",),v.errors,issue.number,v.parent_campaign,v)
    if not v.approved: return Evaluation("ineligible",("issue_not_approved",),("missing_label:"+APPROVAL_LABEL,),issue.number,v.parent_campaign,v)
    return Evaluation("eligible_dry_run",(),(),issue.number,v.parent_campaign,v)

def evaluate_pr(*,pr:Mapping[str,Any],referenced_issues:Sequence[IssuePacket],checks:Sequence[Mapping[str,Any]],reviews:Sequence[Mapping[str,Any]],changed_files:Sequence[Mapping[str,Any]],required_checks:Sequence[str]=REQUIRED_CHECK_NAMES)->Evaluation:
    refs=set(parse_linked_issue_numbers(str(pr.get("body") or ""))); by={x.number:x for x in referenced_issues}; candidates=[]
    for n in sorted(refs):
        if n in by:
            v=validate_issue_packet(by[n])
            if v.parent_campaign is not None: candidates.append((by[n],v))
    if len(candidates)!=1: return Evaluation("missing_lineage",("pr_not_linked_to_issue",),(f"linked_child_count:{len(candidates)}",),None,None,None)
    child,v=candidates[0]
    if not v.valid: return Evaluation("invalid_packet",("issue_packet_invalid",),v.errors,child.number,v.parent_campaign,v)
    blockers=[]; details=[]
    if not v.approved: blockers.append("issue_not_approved"); details.append("missing_label:"+APPROVAL_LABEL)
    if pr.get("draft"): blockers.append("pr_is_draft")
    if str(pr.get("state") or "open").lower()!="open": blockers.append("pr_is_closed")
    missing,failing=evaluate_checks(checks,required_checks)
    if missing: blockers.append("required_checks_missing"); details += ["missing_check:"+x for x in missing]
    if failing: blockers.append("required_checks_failing"); details += ["failing_check:"+x for x in failing]
    if active_requested_changes(reviews): blockers.append("requested_changes_present")
    if str(pr.get("mergeable_state") or pr.get("branch_state") or "unknown").lower()=="behind": blockers.append("branch_out_of_date")
    ok,bad=validate_scope(changed_files,v.allowed_files)
    if not ok: blockers.append("scope_validation_failed"); details += ["unexpected_file:"+x for x in bad]
    ok,findings=validate_privacy(changed_files,v.privacy_required)
    if not ok: blockers.append("privacy_sentinel_failed"); details += list(findings)
    if MERGE_AUTHORITY_LABEL not in labels(pr.get("labels")): blockers.append("merge_authority_missing"); details.append("missing_label:"+MERGE_AUTHORITY_LABEL)
    blockers=tuple(sorted(set(blockers))); return Evaluation("blocked" if blockers else "eligible_dry_run",blockers,tuple(sorted(set(details))),child.number,v.parent_campaign,v)

def normal(value: Any) -> Any:
    if is_dataclass(value): return normal(asdict(value))
    if isinstance(value,Mapping): return {str(k):normal(v) for k,v in sorted(value.items())}
    if isinstance(value,(list,tuple,set,frozenset)): return [normal(x) for x in value]
    return value

def build_receipt(*,event_name:str,event_action:str,repository:str,workflow_run_id:str,workflow_run_attempt:str,target_kind:str,target_number:int|None,evaluation:Evaluation,evidence:Mapping[str,Any])->dict[str,Any]:
    stable={"event_name":event_name,"event_action":event_action,"repository":repository,"target_kind":target_kind,"target_number":target_number,"evaluation":normal(evaluation),"evidence":normal(evidence)}
    decision="sha256:"+hashlib.sha256(json.dumps(stable,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"schema_version":SCHEMA_VERSION,"receipt_key":f"campaign-control-plane:{repository}:{target_kind}:{target_number or 'unknown'}","decision_id":decision,"dry_run":True,"event":{"name":event_name,"action":event_action},"repository":repository,"target":{"kind":target_kind,"number":target_number},"workflow":{"run_id":workflow_run_id,"run_attempt":workflow_run_attempt},"evaluated_at":dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z"),"state":evaluation.state,"blocker_codes":list(evaluation.blockers),"details":list(evaluation.details),"linked_child_issue":evaluation.linked_child_issue,"parent_campaign_issue":evaluation.parent_campaign_issue,"evidence":normal(evidence),"authority":{"model_review_advisory_only":True,"merge_api_called":False,"auto_merge_enabled":False,"branch_updated":False,"repository_settings_mutated":False}}
