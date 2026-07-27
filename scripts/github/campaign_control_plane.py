#!/usr/bin/env python3
"""GitHub API adapter for the campaign control-plane dry run."""
from __future__ import annotations
import argparse, json, os, sys, urllib.error, urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence
from campaign_control_plane_core import *

class ControlPlaneError(RuntimeError): pass
class Client:
    def __init__(self,repo:str,token:str,api:str): self.repo,self.token,self.api=repo,token,api.rstrip("/")
    def get(self,path:str)->Any:
        req=urllib.request.Request(self.api+path,headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+self.token,"X-GitHub-Api-Version":"2022-11-28","User-Agent":"codexify-campaign-control-plane/1"})
        try:
            with urllib.request.urlopen(req,timeout=20) as response: return json.load(response)
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as exc: raise ControlPlaneError(f"GitHub API GET failed for {path}: {exc}") from exc
    def issue(self,n): return self.get(f"/repos/{self.repo}/issues/{n}")
    def pr(self,n): return self.get(f"/repos/{self.repo}/pulls/{n}")
    def reviews(self,n): return self.get(f"/repos/{self.repo}/pulls/{n}/reviews?per_page=100")
    def files(self,n): return self.get(f"/repos/{self.repo}/pulls/{n}/files?per_page=100")
    def checks(self,sha):
        out=list(self.get(f"/repos/{self.repo}/commits/{sha}/check-runs?per_page=100").get("check_runs",[]))
        out += [{"name":x.get("context"),"status":"completed","conclusion":x.get("state")} for x in self.get(f"/repos/{self.repo}/commits/{sha}/status").get("statuses",[])]
        return out

def packet(raw): return IssuePacket(int(raw.get("number") or 0),str(raw.get("body") or ""),labels(raw.get("labels")),str(raw.get("title") or ""))
def target(event,payload):
    if event=="issues": item=payload.get("issue"); return "issue",int(item.get("number")) if isinstance(item,Mapping) else None,item
    if event in {"pull_request","pull_request_review"}: item=payload.get("pull_request"); return "pull_request",int(item.get("number")) if isinstance(item,Mapping) else None,item
    if event=="workflow_run":
        prs=(payload.get("workflow_run") or {}).get("pull_requests") or []; return ("pull_request",int(prs[0]["number"]),None) if prs else ("workflow_run",None,None)
    if event=="workflow_dispatch":
        inputs=payload.get("inputs") or {}
        if inputs.get("pr_number"): return "pull_request",int(inputs["pr_number"]),None
        if inputs.get("issue_number"): return "issue",int(inputs["issue_number"]),None
    return "unknown",None,None

def evaluate_event(event,action,repository,payload,token,api):
    kind,number,embedded=target(event,payload); client=Client(repository,token,api)
    if kind=="issue" and number:
        raw=embedded or client.issue(number); result=evaluate_issue(packet(raw)); return result,{"issue_updated_at":raw.get("updated_at"),"approval_label":APPROVAL_LABEL,"packet_errors":list(result.issue_validation.errors if result.issue_validation else ())},kind,number
    if kind=="pull_request" and number:
        raw=client.pr(number); refs=parse_linked_issue_numbers(str(raw.get("body") or "")); issues=[packet(client.issue(n)) for n in refs]
        sha=str((raw.get("head") or {}).get("sha") or ""); checks=client.checks(sha) if sha else []; reviews,files=client.reviews(number),client.files(number)
        result=evaluate_pr(pr=raw,referenced_issues=issues,checks=checks,reviews=reviews,changed_files=files)
        evidence={"pr_updated_at":raw.get("updated_at"),"head_sha":sha,"referenced_issue_numbers":list(refs),"required_checks":list(REQUIRED_CHECK_NAMES),"observed_check_names":sorted({str(x.get("name") or x.get("context") or "") for x in checks}),"changed_files":sorted(str(x.get("filename")) for x in files),"fork_pr":bool((raw.get("head") or {}).get("repo",{}).get("fork")),"event_source":event}
        return result,evidence,kind,number
    return Evaluation("blocked",("unsupported_event",),(f"event:{event}:{action}",),None,None,None),{"event_source":event},kind,number

def summary(receipt):
    t=receipt.get("target") or {}; blockers=receipt.get("blocker_codes") or []
    return "\n".join(["# Campaign Control Plane Dry Run","",f"- **State:** `{receipt.get('state')}`","- **Dry run:** `true`",f"- **Target:** `{t.get('kind')} #{t.get('number')}`",f"- **Linked child issue:** `{receipt.get('linked_child_issue')}`",f"- **Parent campaign:** `{receipt.get('parent_campaign_issue')}`",f"- **Blockers:** {', '.join('`'+x+'`' for x in blockers) if blockers else 'None'}",f"- **Decision ID:** `{receipt.get('decision_id')}`",f"- **Receipt key:** `{receipt.get('receipt_key')}`","","No merge, auto-merge, branch update, agent dispatch, deployment, or repository-setting mutation was performed.","","```json",json.dumps(receipt,indent=2,sort_keys=True),"```",""])

def valid_body():
    return '''Parent campaign: #625
## Workflow lane
`architecture-impact`
## Task kind
`implementation`
## Context
Bounded.
## Goal
Bounded.
## Files
- scripts/github/campaign_control_plane.py
## Ownership
This change belongs in scripts/github/campaign_control_plane.py
## Acceptance criteria
- Deterministic.
## Non-goals
- No merge.
## Validation
- pytest -q
## Git commands
`git add scripts/github/campaign_control_plane.py`
`git commit -m "feat: add dry run"`
## Expected closeout
- Summary of changes
- Files changed
- Git commit hash
- What Axis should add to his KB
## Board metadata
- Lane: architecture-impact
## Source evidence
- docs/example.md
'''
def self_test():
    issue=IssuePacket(626,valid_body(),(APPROVAL_LABEL,)); assert evaluate_issue(issue).state=="eligible_dry_run"
    checks=[{"name":n,"status":"completed","conclusion":"success"} for n in REQUIRED_CHECK_NAMES]; pr={"body":"Closes #626","draft":False,"state":"open","mergeable_state":"clean","labels":[{"name":MERGE_AUTHORITY_LABEL}]}
    assert evaluate_pr(pr=pr,referenced_issues=[issue],checks=checks,reviews=[],changed_files=[{"filename":"scripts/github/campaign_control_plane.py","patch":"+safe"}]).state=="eligible_dry_run"; print("campaign control-plane self-test passed")
def main(argv:Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--self-test",action="store_true"); p.add_argument("--event-path"); p.add_argument("--event-name",default=os.getenv("GITHUB_EVENT_NAME","workflow_dispatch")); p.add_argument("--event-action",default=""); p.add_argument("--repository",default=os.getenv("GITHUB_REPOSITORY","")); p.add_argument("--run-id",default=os.getenv("GITHUB_RUN_ID","local")); p.add_argument("--run-attempt",default=os.getenv("GITHUB_RUN_ATTEMPT","1")); p.add_argument("--api-url",default=os.getenv("GITHUB_API_URL","https://api.github.com")); p.add_argument("--receipt-path"); p.add_argument("--summary-path",default=os.getenv("GITHUB_STEP_SUMMARY")); args=p.parse_args(argv)
    if args.self_test: self_test(); return 0
    if not args.event_path or not args.repository: p.error("--event-path and --repository are required outside --self-test")
    payload=json.loads(Path(args.event_path).read_text()); action=args.event_action or str(payload.get("action") or "")
    try:
        token=os.getenv("GITHUB_TOKEN","")
        if not token: raise ControlPlaneError("GITHUB_TOKEN is required for event evaluation")
        evaluation,evidence,kind,number=evaluate_event(args.event_name,action,args.repository,payload,token,args.api_url)
    except ControlPlaneError as exc:
        evaluation=Evaluation("blocked",("api_error",),(str(exc)[:240],),None,None,None); evidence={"event_source":args.event_name,"api_error":True}; kind,number,_=target(args.event_name,payload)
    receipt=build_receipt(event_name=args.event_name,event_action=action,repository=args.repository,workflow_run_id=args.run_id,workflow_run_attempt=args.run_attempt,target_kind=kind,target_number=number,evaluation=evaluation,evidence=evidence); text=json.dumps(receipt,indent=2,sort_keys=True)+"\n"
    Path(args.receipt_path).write_text(text) if args.receipt_path else sys.stdout.write(text)
    if args.summary_path:
        with Path(args.summary_path).open("a") as handle: handle.write(summary(receipt))
    return 0
if __name__=="__main__": raise SystemExit(main())
