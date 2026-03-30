---
description: End session — verify tests, update harness artifacts, commit
---

Confirm the feature passes end-to-end (including Temporal/API checks if applicable).
Update `feature_list.json` — set `passes: true` only for the completed feature id.
Append a row to `AUDIT_TRAIL.md` (21 CFR Part 11 table) with session summary — no PHI.
Commit with message `feat(F###): <concise description>`.
