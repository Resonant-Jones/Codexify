"""Bind the Guardian CI run matrix to the properties it is supposed to have.

This file exists because the CI workflow is the thing that decides whether the
rest of the suite is reported as having run. A workflow change cannot be
proven by a green workflow run — the workflow is what runs the test — so the
properties are asserted here instead, by executing the workflow's OWN step
bodies.

Two things this test deliberately does NOT do:

* It does not reimplement the matrix. The `Compute run matrix` step body is
  extracted out of `.github/workflows/guardian-ci.yml` and the GitHub
  expressions are rendered, so the assertions below describe the workflow as
  it is written. A test that hard-coded the matrix would stay green if
  someone reordered the branches — which is exactly the bug this file was
  written to catch.
* It does not assert only outcomes. It also asserts the ORDERING constraint,
  because "the tip of main forces execution" must come after "a superseded
  revision is skipped". Putting it earlier would spend forty minutes of
  runner time on a revision nobody ships, and that is easy to break with a
  well-meaning edit.

The scenarios below are the specification. The headline one is
`push_tip_of_main_docs_only` -> the backend suite runs. It is the case that
produced a green "Backend Tests" check whose pytest step never ran.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("pyyaml not installed", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "guardian-ci.yml"

SUPERSEDED_STEP_NAME = "Detect a superseded revision on main"
COMPUTE_STEP_NAME = "Compute run matrix"


# --------------------------------------------------------------------- load


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _step(name: str) -> dict:
    """Return a named step from the `changes` job."""
    steps = _workflow()["jobs"]["changes"]["steps"]
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(
        f"the workflow no longer has a step named {name!r}; "
        "this contract has to be updated to match, not deleted"
    )


def _step_body(name: str) -> str:
    return _step(name)["run"]


SUPERSEDED_BODY = _step_body(SUPERSEDED_STEP_NAME)
COMPUTE_BODY = _step_body(COMPUTE_STEP_NAME)


# ------------------------------------------------------------------ render


def _render(body: str, context: dict[str, str]) -> str:
    """Replace every GitHub expression with a plain shell value.

    An expression that is not in the context is an error rather than an empty
    string: a new expression in the workflow must make this test fail loudly
    so the scenario table is extended deliberately.
    """

    def substitute(match: re.Match) -> str:
        expression = match.group(1).strip()
        if expression not in context:
            raise AssertionError(
                f"the workflow uses an expression this contract does not know: "
                f"{expression!r}. Add it to the scenario table rather than "
                f"letting it render as an empty value."
            )
        return context[expression]

    return re.sub(r"\$\{\{(.*?)\}\}", substitute, body)


_COMPARISON = re.compile(r"^\s*(?P<left>[A-Za-z0-9_.\-]+)\s*(?P<op>==|!=)\s*'(?P<right>[^']*)'\s*$")


def _evaluate_if(condition: str | None, context: dict[str, str]) -> bool:
    """Evaluate a step's `if:` condition against a context.

    Only the form the workflow actually uses is supported: `&&`-separated
    comparisons of a context key against a quoted literal. The condition is
    read out of the workflow rather than restated here, so this does not
    reimplement the workflow's own gate.
    """
    if condition is None:
        return True
    terms = [term for term in condition.split("&&") if term.strip()]
    assert terms, f"the workflow has an `if:` condition this contract cannot read: {condition!r}"
    for term in terms:
        match = _COMPARISON.match(term)
        assert match, (
            f"the workflow has an `if:` condition this contract cannot read: {term!r}. "
            f"Extend _evaluate_if rather than guessing."
        )
        left = match.group("left")
        assert left in context, f"the `if:` condition reads {left!r}, which is not in the context"
        actual = context[left]
        expected = match.group("right")
        if match.group("op") == "==":
            if actual != expected:
                return False
        else:
            if actual == expected:
                return False
    return True


# ------------------------------------------------------------------- execute


def _run(body: str, context: dict[str, str], tmp_path: Path, *, remote_tip: str | None):
    """Execute a rendered step body and return the outputs it wrote.

    `remote_tip` is what `git ls-remote origin refs/heads/main` reports. It is
    injected through a `git` shim on PATH so the real step body runs
    unmodified and without touching the network. `None` means the remote
    cannot be resolved, which is the fail-open case.
    """
    bindir = tmp_path / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    if remote_tip is None:
        shim = "#!/bin/sh\nexit 0\n"
    else:
        shim = f"#!/bin/sh\nprintf '%s\\trefs/heads/main\\n' '{remote_tip}'\n"
    git_shim = bindir / "git"
    git_shim.write_text(shim, encoding="utf-8")
    git_shim.chmod(0o755)

    output_file = tmp_path / "github_output"
    output_file.write_text("", encoding="utf-8")

    env = dict(os.environ)
    env["PATH"] = f"{bindir}:{env.get('PATH', '')}"
    env["GITHUB_OUTPUT"] = str(output_file)
    env["GITHUB_SHA"] = context["github.sha"]

    completed = subprocess.run(
        ["bash", "-c", body],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    outputs: dict[str, str] = {}
    for line in output_file.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            outputs[key.strip()] = value.strip()

    return completed, outputs


def _resolve_superseded(
    tmp_path: Path,
    *,
    event: str,
    ref: str,
    revision: str,
    remote_tip: str | None,
) -> str:
    """Run the real superseded-revision step and return its verdict.

    The step is only executed when its own `if:` condition holds, which is
    read out of the workflow. When it does not run, the workflow sees no
    `superseded` output at all, which the compute step reads as "not
    superseded" — exactly what the real workflow does.
    """
    condition = _step(SUPERSEDED_STEP_NAME).get("if")
    context = {"github.event_name": event, "github.ref": ref, "github.sha": revision}
    if not _evaluate_if(condition, context):
        return "false"

    body = _render(SUPERSEDED_BODY, context)
    completed, outputs = _run(body, context, tmp_path, remote_tip=remote_tip)
    assert completed.returncode == 0, (
        f"the superseded-revision step failed: {completed.stderr.strip()}"
    )
    return outputs.get("superseded", "false")


def _compute_matrix(
    tmp_path: Path,
    *,
    event: str,
    ref: str,
    revision: str,
    remote_tip: str | None,
    backend: str,
    frontend: str,
    ci: str,
    shared: str,
) -> dict[str, str]:
    """Run the superseded step, then the compute step, and return the outputs."""
    superseded = _resolve_superseded(
        tmp_path, event=event, ref=ref, revision=revision, remote_tip=remote_tip
    )
    context = {
        "github.event_name": event,
        "github.ref": ref,
        "github.sha": revision,
        "steps.filter.outputs.backend": backend,
        "steps.filter.outputs.frontend": frontend,
        "steps.filter.outputs.ci": ci,
        "steps.filter.outputs.shared": shared,
        "steps.superseded.outputs.superseded": superseded,
    }
    body = _render(COMPUTE_BODY, context)
    completed, outputs = _run(body, context, tmp_path, remote_tip=remote_tip)
    assert completed.returncode == 0, (
        f"the compute-matrix step failed: {completed.stderr.strip()}"
    )
    return outputs


# ---------------------------------------------------------------- scenarios

REVISION = "0123456789abcdef0123456789abcdef01234567"
OTHER_REVISION = "fedcba9876543210fedcba9876543210fedcba98"

# name, event, ref, remote_tip, backend, frontend, ci, shared, run_backend, run_frontend
#
# `remote_tip` is what the remote reports as the tip of main. It equals the
# revision under test for a tip-of-main scenario, and differs for a
# superseded one. It is irrelevant for pull requests and non-main branches,
# because the superseded step's own `if:` excludes them.
SCENARIOS = [
    ("push_tip_of_main_docs_only", "push", "refs/heads/main", REVISION,
     "false", "false", "false", "false", "true", "true"),
    ("push_tip_of_main_backend_changed", "push", "refs/heads/main", REVISION,
     "true", "false", "false", "false", "true", "true"),
    ("push_tip_of_main_frontend_changed", "push", "refs/heads/main", REVISION,
     "false", "true", "false", "false", "true", "true"),
    ("push_tip_of_main_ci_changed", "push", "refs/heads/main", REVISION,
     "false", "false", "true", "false", "true", "true"),
    ("push_superseded_revision", "push", "refs/heads/main", OTHER_REVISION,
     "true", "false", "false", "false", "false", "false"),
    ("push_superseded_revision_docs_only", "push", "refs/heads/main", OTHER_REVISION,
     "false", "false", "false", "false", "false", "false"),
    ("manual_dispatch_docs_only", "workflow_dispatch", "refs/heads/main", REVISION,
     "false", "false", "false", "false", "true", "false"),
    ("pull_request_backend_changed", "pull_request", "refs/pull/7/merge", OTHER_REVISION,
     "true", "false", "false", "false", "true", "false"),
    ("pull_request_docs_only", "pull_request", "refs/pull/7/merge", OTHER_REVISION,
     "false", "false", "false", "false", "false", "false"),
    ("pull_request_ci_changed", "pull_request", "refs/pull/7/merge", OTHER_REVISION,
     "false", "false", "true", "false", "true", "true"),
    ("push_feature_branch_docs_only", "push", "refs/heads/feature/x", OTHER_REVISION,
     "false", "false", "false", "false", "false", "false"),
    ("push_feature_branch_backend_changed", "push", "refs/heads/feature/x", OTHER_REVISION,
     "true", "false", "false", "false", "true", "false"),
]


@pytest.mark.parametrize(
    ("name", "event", "ref", "remote_tip", "backend", "frontend", "ci", "shared",
     "expected_backend", "expected_frontend"),
    SCENARIOS,
    ids=[scenario[0] for scenario in SCENARIOS],
)
def test_run_matrix_scenario(
    tmp_path: Path,
    name: str,
    event: str,
    ref: str,
    remote_tip: str,
    backend: str,
    frontend: str,
    ci: str,
    shared: str,
    expected_backend: str,
    expected_frontend: str,
) -> None:
    """Every documented scenario resolves to the run matrix it is supposed to.

    `push_tip_of_main_docs_only` is the one that matters most: a
    documentation-only push to the tip of main must still execute the suite,
    so a green "Backend Tests" check can never mean "the pytest step was
    skipped".
    """
    outputs = _compute_matrix(
        tmp_path,
        event=event,
        ref=ref,
        revision=REVISION,
        remote_tip=remote_tip,
        backend=backend,
        frontend=frontend,
        ci=ci,
        shared=shared,
    )
    assert outputs.get("run_backend") == expected_backend, (
        f"{name}: run_backend was {outputs.get('run_backend')!r}, "
        f"expected {expected_backend!r}"
    )
    assert outputs.get("run_frontend") == expected_frontend, (
        f"{name}: run_frontend was {outputs.get('run_frontend')!r}, "
        f"expected {expected_frontend!r}"
    )


def test_tip_of_main_branch_is_ordered_after_the_superseded_check() -> None:
    """The tip-of-main branch must come AFTER the superseded branch.

    Before the superseded branch, a revision nobody ships would run the suite
    anyway and spend forty minutes of runner time on it. The scenario table
    above would also catch that, but only as a failure someone has to
    re-derive; this names the invariant directly.
    """
    superseded_at = COMPUTE_BODY.find("steps.superseded.outputs.superseded")
    assert superseded_at != -1, (
        "the compute-matrix step no longer reads the superseded verdict; "
        "the superseded check and this contract have drifted apart"
    )

    tip_branch = re.search(
        r"elif\s+\[\s*\"\$\{\{\s*github\.event_name\s*\}\}\"\s*=\s*\"push\"\s*\]"
        r"\s*&&\s*\[\s*\"\$\{\{\s*github\.ref\s*\}\}\"\s*=\s*\"refs/heads/main\"\s*\]",
        COMPUTE_BODY,
    )
    assert tip_branch is not None, (
        "the compute-matrix step no longer forces execution for the tip of "
        "main; a green backend check on main can once again mean nothing"
    )

    assert tip_branch.start() > superseded_at, (
        "the tip-of-main branch must be evaluated after the superseded "
        "check, or a revision that is no longer the tip of main will run "
        "the suite anyway"
    )


def test_superseded_check_fails_open_when_the_tip_cannot_be_resolved(tmp_path: Path) -> None:
    """An unresolvable remote tip is treated as current, not as superseded.

    The workflow says so in its own words: "Could not resolve the tip of
    main; treating this revision as current." That is the safe direction —
    it runs the suite instead of skipping it — and it is asserted here so a
    well-meaning edit cannot quietly invert it into a silent skip.
    """
    verdict = _resolve_superseded(
        tmp_path,
        event="push",
        ref="refs/heads/main",
        revision=REVISION,
        remote_tip=None,
    )
    assert verdict == "false", (
        "an unresolvable remote tip must not mark the revision superseded"
    )


def test_superseded_check_marks_a_stale_revision(tmp_path: Path) -> None:
    """A revision that is not the remote tip is marked superseded."""
    verdict = _resolve_superseded(
        tmp_path,
        event="push",
        ref="refs/heads/main",
        revision=REVISION,
        remote_tip=OTHER_REVISION,
    )
    assert verdict == "true", (
        "a revision that is not the tip of main must be marked superseded"
    )


def test_superseded_check_treats_the_tip_as_current(tmp_path: Path) -> None:
    """A revision that IS the remote tip is not marked superseded."""
    verdict = _resolve_superseded(
        tmp_path,
        event="push",
        ref="refs/heads/main",
        revision=REVISION,
        remote_tip=REVISION,
    )
    assert verdict == "false", (
        "the tip of main must not be marked superseded"
    )


def test_superseded_check_does_not_run_off_main(tmp_path: Path) -> None:
    """The superseded check only runs for a push to main.

    Read out of the workflow's own `if:` condition rather than restated, so
    a change to that gate has to be made deliberately.
    """
    verdict = _resolve_superseded(
        tmp_path,
        event="pull_request",
        ref="refs/pull/7/merge",
        revision=REVISION,
        remote_tip=OTHER_REVISION,
    )
    assert verdict == "false", (
        "the superseded check must not run outside a push to main"
    )
