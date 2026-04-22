"""Post-completion evaluation spine."""

from guardian.evals.groundedness import evaluate_groundedness
from guardian.evals.spine import (
    EVAL_QUEUE_NAME,
    build_trace_snapshot,
    enqueue_post_completion_eval,
    get_latest_eval_diagnostics,
    persist_eval_verdicts,
    persist_trace_snapshot,
)

__all__ = [
    "EVAL_QUEUE_NAME",
    "build_trace_snapshot",
    "enqueue_post_completion_eval",
    "evaluate_groundedness",
    "get_latest_eval_diagnostics",
    "persist_eval_verdicts",
    "persist_trace_snapshot",
]
