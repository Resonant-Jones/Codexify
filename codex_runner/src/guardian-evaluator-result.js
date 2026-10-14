/** Bounded, content-minimizing ADR-068 Evaluator result projection. */

export const EVALUATOR_RESULT_CONTRACT = "campaign-evaluator-v0";

const VERDICTS = new Set([
	"passed", "passed_with_advisories", "repair_required", "blocked",
]);
const CRITERION_VERDICTS = new Set(["pass", "fail", "advisory"]);
const SAFE_REF = /^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,127}$/;
const CREDENTIAL_SHAPE = /\bsk-[A-Za-z0-9_-]{16,}|Bearer\s+\S{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:api[_-]?key|password|secret)\s*[:=]\s*\S{8,}/i;

function exactKeys(value, names) {
	return value !== null && typeof value === "object" && !Array.isArray(value)
		&& Object.keys(value).length === names.length
		&& names.every((name) => Object.hasOwn(value, name));
}

function boundedText(value, maximum) {
	return typeof value === "string" && value.length > 0 && value.length <= maximum
		&& value.trim().length > 0
		&& !CREDENTIAL_SHAPE.test(value);
}

export function projectGuardianEvaluatorResult(value) {
	if (!exactKeys(value, ["verdict", "summary", "structured_acceptance_results"])
		|| !VERDICTS.has(value.verdict)
		|| !boundedText(value.summary, 500)
		|| !Array.isArray(value.structured_acceptance_results)
		|| value.structured_acceptance_results.length < 1
		|| value.structured_acceptance_results.length > 16) {
		throw new Error("guardian_evaluator_result_invalid");
	}
	const seen = new Set();
	const results = value.structured_acceptance_results.map((item) => {
		if (!exactKeys(item, ["criterion_id", "verdict", "evidence_refs", "basis"])
			|| !SAFE_REF.test(item.criterion_id)
			|| seen.has(item.criterion_id)
			|| !CRITERION_VERDICTS.has(item.verdict)
			|| !Array.isArray(item.evidence_refs)
			|| item.evidence_refs.length < 1
			|| item.evidence_refs.length > 8
			|| !item.evidence_refs.every((ref) => typeof ref === "string" && SAFE_REF.test(ref))
			|| !boundedText(item.basis, 500)) {
			throw new Error("guardian_evaluator_result_invalid");
		}
		seen.add(item.criterion_id);
		return {
			criterion_id: item.criterion_id,
			verdict: item.verdict,
			evidence_refs: [...item.evidence_refs],
			basis: item.basis,
		};
	});
	const criterionVerdicts = new Set(results.map((item) => item.verdict));
	if ((value.verdict === "passed" && (criterionVerdicts.size !== 1 || !criterionVerdicts.has("pass")))
		|| (value.verdict === "passed_with_advisories" && (criterionVerdicts.has("fail") || !criterionVerdicts.has("advisory")))
		|| (value.verdict === "repair_required" && !criterionVerdicts.has("fail"))) {
		throw new Error("guardian_evaluator_result_invalid");
	}
	return {
		verdict: value.verdict,
		summary: value.summary,
		structured_acceptance_results: results,
	};
}
