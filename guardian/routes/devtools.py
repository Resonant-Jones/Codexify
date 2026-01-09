"""
Devtools Routes
~~~~~~~~~~~~~~~

Development and debugging endpoints for inspecting system state.
These endpoints are intended for local development and debugging only.
"""

import logging

from fastapi import APIRouter

from guardian.tools.state_inspector import get_codexify_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["Devtools"])


@router.get("/state/{thread_id}")
def get_dev_state(thread_id: str):
    """
    Get the current state of a thread for debugging purposes.

    Performs a full health check across MVP-critical surfaces:
    - Thread existence and message count
    - Persona attachment status
    - Context bundle readiness
    - Linked documents and images
    - Agent target readiness

    Args:
        thread_id: The thread identifier to inspect

    Returns:
        Structured state report as JSON
    """
    logger.info(
        "[devtools] state inspection requested for thread=%s", thread_id
    )
    return get_codexify_state(thread_id)
