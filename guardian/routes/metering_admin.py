"""Read-only account inference usage, guarded by existing account-admin auth."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from guardian.core.db import load_guardian_db_from_env
from guardian.metering.ledger import account_inference_totals
from guardian.metering.budget import budget_status
from guardian.metering.runtime import configuration
from guardian.routes.account_observability import _require_account_admin

router = APIRouter(prefix="/api/admin/metering", tags=["Admin Metering"])


@router.get("/inference")
def inference_totals(
    account_id: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=100, ge=1, le=100),
    _admin: str = Depends(_require_account_admin),
) -> dict:
    """Only canonical account admins may read cross-account totals."""
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(status_code=503, detail="Metering database unavailable")
    try:
        with db.get_session() as session:
            accounts = account_inference_totals(
                session, account_id=account_id, limit=limit
            )
            config = configuration()
            guarded = (
                budget_status(
                    session,
                    monthly_window=config["monthly_window"],
                    funding_window=config["funding_window"],
                    account_id=account_id,
                    limit=limit,
                    account_allowances=config.get("account_allowances"),
                )
                if config is not None
                else None
            )
        result = {
            "service": "inference",
            "mode": "observe_only",
            "accounts": accounts,
            "cost_basis": "configured_rate_snapshot_estimate",
            "unpriced_usage_is_not_zero": True,
        }
        if guarded is not None:
            result["bounded_budget"] = guarded
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Metering read unavailable"
        ) from exc
