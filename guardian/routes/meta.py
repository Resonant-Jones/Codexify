"""
Meta / Self-Check Routes
~~~~~~~~~~~~~~~~~~~~~~~~~

Self-diagnostic endpoints for quick runtime status checks.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

# Import self-check function
try:
    from guardian.self_check import epistemic_self_check
except ImportError:

    def epistemic_self_check(*args, **kwargs):
        return {"error": "epistemic_self_check not available"}


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/selfcheck")
async def meta_selfcheck():
    result = epistemic_self_check(
        intent="runtime_status",
        available_functions=["base_operation", "query_processing"],
        context={"system": "guardian_api"},
    )
    try:
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "selfcheck.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")
    except Exception as _e:
        logger.debug("[meta] failed to write selfcheck log: %s", _e)
    return result
