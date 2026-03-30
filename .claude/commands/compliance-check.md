---
description: Tier 1 — verify 21 CFR Part 11 and harness gates before merge
---

Verify:

- Electronic signature stubs include identity, intent (meaning), timestamp, and method.
- Audit trail module does not log raw PHI; only ids and correlation_id.
- `AUDIT_TRAIL.md` has a new entry for this change set.
- `config/fda-compliance.yaml` policies still match code enums where applicable.
- Data integrity: checksum algorithm documented as SHA-256 for artifacts.

Report PASS/FAIL and list gaps.
