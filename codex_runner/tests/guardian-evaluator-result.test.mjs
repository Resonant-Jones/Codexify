import assert from "node:assert/strict";
import test from "node:test";

import { projectGuardianEvaluatorResult } from "../src/guardian-evaluator-result.js";

const valid = () => ({
	verdict: "passed",
	summary: "The allowed file contains the exact marker.",
	structured_acceptance_results: [{
		criterion_id: "exact-marker",
		verdict: "pass",
		evidence_refs: ["changed-files", "target-snapshot"],
		basis: "The bounded diff shows the exact marker.",
	}],
});

test("projects only the bounded canonical verdict", () => {
	assert.deepEqual(projectGuardianEvaluatorResult(valid()), valid());
});

test("rejects extra response content and credentials", () => {
	assert.throws(() => projectGuardianEvaluatorResult({ ...valid(), reasoning: "hidden" }));
	assert.throws(() => projectGuardianEvaluatorResult({ ...valid(), summary: "Bearer abcdefgh12345678" }));
});

test("rejects inconsistent and oversized verdicts", () => {
	const failed = valid();
	failed.structured_acceptance_results[0].verdict = "fail";
	assert.throws(() => projectGuardianEvaluatorResult(failed));
	const long = valid();
	long.summary = "x".repeat(501);
	assert.throws(() => projectGuardianEvaluatorResult(long));
});
