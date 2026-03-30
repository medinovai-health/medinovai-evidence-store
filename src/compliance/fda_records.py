"""Record retention policies (21 CFR Part 11 aligned scaffolding)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class MosRetentionPolicy(str, Enum):
    """Named retention policies."""

    CLINICAL_TRIAL_25Y = "clinical_trial_25y"
    RESEARCH_7Y = "research_7y"
    OPERATIONAL_3Y = "operational_3y"


@dataclass(frozen=True)
class MosRetentionRule:
    """Years until expiry and WORM behavior."""

    policy: MosRetentionPolicy
    years: int
    worm_on_archive: bool


E_RETENTION_RULES: dict[MosRetentionPolicy, MosRetentionRule] = {
    MosRetentionPolicy.CLINICAL_TRIAL_25Y: MosRetentionRule(
        MosRetentionPolicy.CLINICAL_TRIAL_25Y, 25, True
    ),
    MosRetentionPolicy.RESEARCH_7Y: MosRetentionRule(MosRetentionPolicy.RESEARCH_7Y, 7, False),
    MosRetentionPolicy.OPERATIONAL_3Y: MosRetentionRule(
        MosRetentionPolicy.OPERATIONAL_3Y, 3, False
    ),
}


def mos_compute_expires_at(
    mos_policy: MosRetentionPolicy,
    mos_archived_at: datetime | None = None,
) -> datetime:
    """Compute expiry datetime from archive time (UTC)."""
    mos_base = mos_archived_at or datetime.now(timezone.utc)
    mos_rule = E_RETENTION_RULES[mos_policy]
    return mos_base + timedelta(days=365 * mos_rule.years)
