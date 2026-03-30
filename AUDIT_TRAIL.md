# Audit Trail — medinovai-evidence-store

**Format:** FDA 21 CFR Part 11 — electronic records audit trail (reference implementation)  
**System:** medinovai-evidence-store  
**Version:** 0.1.0  

## Regulatory basis

| Requirement | Implementation (target) |
|-------------|-------------------------|
| §11.10(e) — Audit trails | Immutable, time-ordered events with actor, action, object, reason |
| §11.10(d) — Authority checks | RBAC via MSS / SpiceDB (integrate in production) |
| §11.50 — Signature manifestations | Signer identity, timestamp, meaning of signature |
| §11.70 — Signature/record linking | Cryptographic binding via record checksums |

## Trail entries

| Timestamp (UTC) | Session / Actor | Event | Object ID | Reason / Detail | PHI-safe |
|-----------------|-----------------|-------|-----------|-----------------|----------|
| 2026-03-30T00:00:00Z | system / initializer | REPO_INIT | repo:medinovai-evidence-store | Harness scaffold created; no runtime PHI | yes |

## Instructions for agents

1. Append one row per state-changing session or merged feature.
2. Use **correlation_id** in API logs; mirror summary here without raw PHI.
3. Never paste patient names, MRNs, or free-text clinical data.

## Revision history

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-03-30 | Platform | Initial audit trail template |
