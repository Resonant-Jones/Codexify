GH_WORKFLOW ?= codemap-maintenance.yml
GH_WORKFLOW_TITLE ?= Codemap maintenance
REF ?= $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)

.PHONY: codemap-help gh-check codemap-workflow-run codemap-workflow-wait \
        codemap-workflow-open codemap-workflow-status codemap-workflow-latest \
        codemap-artifact codemap-artifact-clean codemap-workflow-run-now codemap-workflow-logs

codemap-help: ## list codemap targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/: /' | sort

gh-check: ## verify gh auth
	@gh --version >/dev/null || { echo "Install GitHub CLI"; exit 1; }
	@gh auth status >/dev/null || { echo "Run: gh auth login"; exit 1; }

codemap-workflow-run: gh-check ## trigger workflow on REF
	gh workflow run $(GH_WORKFLOW) --ref $(REF)

codemap-workflow-status: gh-check ## list recent runs
	gh run list --workflow="$(GH_WORKFLOW_TITLE)" --limit 5

codemap-workflow-latest: gh-check ## show latest run
	gh run list --workflow="$(GH_WORKFLOW_TITLE)" --limit 1 --json databaseId,displayTitle,headBranch,status,url | jq .

codemap-workflow-wait: gh-check ## wait for latest run
	@RID=$$(gh run list --workflow="$(GH_WORKFLOW_TITLE)" --limit 1 --json databaseId --jq '.[0].databaseId'); \
	test -n "$$RID" && gh run watch "$$RID" || { echo "No runs found"; exit 1; }

codemap-workflow-open: gh-check ## open latest run
	@URL=$$(gh run list --workflow="$(GH_WORKFLOW_TITLE)" --limit 1 --json url --jq '.[0].url'); \
	(open "$$URL" 2>/dev/null || xdg-open "$$URL" 2>/dev/null || echo "$$URL")

codemap-artifact: gh-check ## download latest artifact to tmp/codemap
	@RID=$$(gh run list --workflow="$(GH_WORKFLOW_TITLE)" --limit 1 --json databaseId --jq '.[0].databaseId'); \
	test -n "$$RID" && mkdir -p tmp/codemap && gh run download "$$RID" -n codemap-"$$RID" -D tmp/codemap && ls -lah tmp/codemap

codemap-artifact-clean: ## remove tmp/codemap
	rm -rf tmp/codemap

codemap-workflow-run-now: codemap-workflow-run codemap-workflow-wait codemap-artifact ## trigger→wait→fetch

codemap-workflow-logs: gh-check ## print logs for latest run
	@RID=$$(gh run list --workflow="$(GH_WORKFLOW_TITLE)" --limit 1 --json databaseId --jq '.[0].databaseId'); \
	test -n "$$RID" && gh run view "$$RID" --log
