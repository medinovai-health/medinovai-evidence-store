"""Electronic signature model and validation (21 CFR Part 11 §11.50, §11.70)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MosSignatureMeaning(str, Enum):
    """Permitted signature meanings (Part 11 manifestation)."""

    AUTHORSHIP = "authorship"
    REVIEW = "review"
    APPROVAL = "approval"
    RESPONSIBILITY = "responsibility"


class MosSignatureMethod(str, Enum):
    """Identity verification method."""

    PASSWORD = "password"
    BIOMETRIC = "biometric"
    TWO_FACTOR = "two_factor"


class MosElectronicSignature(BaseModel):
    """Electronic signature record bound to a workflow or artifact."""

    signature_id: str = Field(default_factory=lambda: str(uuid4()))
    signer_id: str
    signer_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meaning: MosSignatureMeaning
    method: MosSignatureMethod
    intent_statement: str = Field(
        ...,
        description="Human-readable intent (e.g. I approve protocol v3).",
    )
    record_checksum_sha256: str | None = None


def mos_validate_signature_payload(mos_sig: MosElectronicSignature) -> dict[str, Any]:
    """Validate required Part 11 fields; returns dict safe for audit (no PHI).

    Args:
        mos_sig: Parsed signature payload.

    Returns:
        Serializable summary for audit_trail.

    Raises:
        ValueError: If required intent or identity fields are missing.
    """
    if not mos_sig.intent_statement.strip():
        raise ValueError("intent_statement required for Part 11 signature")
    if not mos_sig.signer_id.strip() or not mos_sig.signer_name.strip():
        raise ValueError("signer identity required")
    return {
        "signature_id": mos_sig.signature_id,
        "signer_id": mos_sig.signer_id,
        "meaning": mos_sig.meaning.value,
        "method": mos_sig.method.value,
        "timestamp": mos_sig.timestamp.isoformat(),
        "phi_safe": True,
    }
