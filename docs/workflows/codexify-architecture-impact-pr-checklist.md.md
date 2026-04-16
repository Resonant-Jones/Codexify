# Codexify Architecture-Impact PR Checklist

Use this checklist for any PR that changes:

* runtime semantics
* retrieval policy or routing doctrine
* control-plane behavior
* queue / worker / acceptance contracts
* identity boundaries
* observability truth surfaces
* canonical token domains

If none of those are affected, use the standard PR flow instead.

---

## PR Classification

* [ ] This PR is **architecture-impacting**
* [ ] This PR is **not** architecture-impacting and does **not** need ADR review

---

## Current-Truth Review

* [ ] I read `docs/architecture/00-current-state.md`
* [ ] I verified the change does not contradict current supported reality
* [ ] I checked whether this change affects anything currently listed as:

  * supported
  * not yet true
  * active blocker
  * current priority

---

## ADR Review

* [ ] I read `docs/architecture/adr/ADR Index.md`
* [ ] I identified the governing ADR(s), if any
* [ ] This PR is:

  * [ ] aligned with an existing ADR
  * [ ] introducing a new ADR
  * [ ] superseding an existing ADR
  * [ ] not ADR-impacting

### ADR impact note

Fill this in inside the PR body:

```text id="5k8jny"
ADR impact:
- classification: <no ADR impact | aligned | new ADR | supersedes>
- governing ADRs: <ADR ids/titles or none>
- reason: <1–3 sentences>
```

---

## Contract / Invariant Check

* [ ] I identified the relevant contract docs
* [ ] I verified the change preserves existing invariants unless this PR explicitly changes them
* [ ] I did **not** silently change a system truth surface

Examples of invariants to check:

* route acceptance does not imply completion
* provider state and request state remain separate
* message identity and request identity remain separate
* retrieval policy is not derived from prompt text
* frontend does not invent backend truth
* override does not replace policy
* thread-first retrieval remains intact
* identity boundaries remain intact

---

## Proof Surface

* [ ] I identified the correct proof surface for this change
* [ ] I ran the relevant seam tests, runtime proof, or docs validation
* [ ] I did **not** rely on unrelated green tests as proof

Examples:

* backend seam tests
* frontend contract tests
* trace/debug seam tests
* broker seam tests
* docs-only link/path validation
* supported-path live proof

---

## Documentation Follow-Through

* [ ] I updated docs that changed meaningfully
* [ ] I explicitly decided which docs did **not** need updating
* [ ] I did **not** leave architecture drift behind

Possible docs to update:

* `docs/architecture/00-current-state.md`
* `docs/architecture/adr/ADR Index.md`
* `docs/architecture/architecture-atlas.md`
* `docs/architecture/README.md`
* `docs/architecture/router-decision-table.md`
* `docs/architecture/chat-runtime-contract.md`
* `docs/architecture/tech-debt-and-risks.md`

---

## PR Body Minimum

Every architecture-impacting PR should include:

```text id="qz8cds"
## Summary
<what changed>

## Current-truth anchors
- ...
- ...

## ADR impact
- classification:
- governing ADRs:
- reason:

## Invariants checked
1. ...
2. ...
3. ...

## Proof surface
- commands run:
- result:

## Documentation follow-through
- updated:
- intentionally unchanged:
```

---

## Final Gate

* [ ] This PR changes implementation **without** smuggling in undocumented architecture changes
* [ ] This PR either references the right ADRs or adds a new ADR
* [ ] This PR leaves the repo easier to reason about than before
