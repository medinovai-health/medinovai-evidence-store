"""Electronic signature tasks invoked as Temporal activities (Part 11 hooks)."""

from __future__ import annotations

from datetime import timedelta

import structlog
from temporalio import activity

from src.compliance.electronic_signature import (
    MosElectronicSignature,
    mos_validate_signature_payload,
)

mos_logger = structlog.get_logger()

E_ACTIVITY_VERIFY_SIG = "verify_electronic_signature"


@activity.defn(name=E_ACTIVITY_VERIFY_SIG)
async def mos_activity_verify_electronic_signature(
    mos_payload: dict,
) -> dict:
    """Validate signature fields and return audit-safe summary.

    Args:
        mos_payload: Serialized MosElectronicSignature fields.

    Returns:
        Validation summary for binding to workflow state.
    """
    mos_sig = MosElectronicSignature.model_validate(mos_payload)
    mos_summary = mos_validate_signature_payload(mos_sig)
    mos_logger.info(
        "signature_verified",
        signature_id=mos_summary["signature_id"],
        phi_safe=True,
    )
    return mos_summary


def mos_signature_activity_timeout() -> timedelta:
    """Timeout for signature verification activity."""
    return timedelta(seconds=30)
