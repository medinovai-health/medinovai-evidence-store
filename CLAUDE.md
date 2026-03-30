# CLAUDE.md — medinovai-evidence-store

> This file is read by every Claude agent at the start of each session.
> Keep it accurate. It is the agent's primary source of truth about this repo.

## Purpose

The Evidence Store is a **Phase F Tier 1** MedinovAI service that orchestrates **clinical/research study lifecycles** with **Temporal** workflows, manages **analysis artifacts** with **versioning and provenance graphs**, exports **reproducibility bundles** for regulatory submission, and enforces **FDA 21 CFR Part 11** controls (electronic signatures with identity verification, immutable audit trails, checksum-based data integrity, and retention policies). It integrates with platform security (MSS) and must never log PHI—use study and artifact IDs only.

## Compliance Tier

**Tier 1 — Full compliance harness**

| Annotation | Meaning |
|------------|---------|
| **Tier 1** | AUDIT_TRAIL.md required; session append; IEC 62304 traceability via `feature_list.json` |
| **21 CFR Part 11** | Electronic records and signatures; who/what/when/why; non-repudiation hooks |
| **HIPAA / GDPR** | No PHI in logs; tenant isolation; access events to audit pipeline |
| **IEC 62304** | Features map to verifiable test steps; change control via git + audit trail |

Applicable regulations: **21 CFR Part 11**, **HIPAA**, **GDPR**, **IEC 62304** (software lifecycle traceability for regulated workflows).

## Tech Stack

- Backend: Python 3.11+, FastAPI, `temporalio` Python SDK
- Workflow engine: Temporal Server (see `docker-compose.yml`)
- Database: Postgres (Temporal); application persistence TBD (out of scaffold scope)
- Cache: None (scaffold)
- Messaging: Temporal task queues (`E_TASK_QUEUE_DEFAULT`)
- Infrastructure: Docker Compose (local); Kubernetes reference TBD
- Monitoring: Structured JSON logs (structlog / ZTA-style fields)

## How to Start the Dev Server

```bash
bash init.sh
```

API default: `http://localhost:8000`  
Health: `GET /health` → 200 JSON  
Readiness: `GET /ready` → 200 JSON  

## How to Run Unit Tests

```bash
. .venv/bin/activate
pytest tests/ -q
```

Minimum coverage target: **80%** (not enforced until tests exist).

## How to Run End-to-End Tests

```bash
# After Temporal + API are up (see init.sh)
pytest tests/e2e/ -q
```

E2E scaffold: add Playwright or HTTP workflow tests in later sessions.

## Coding Conventions (MedinovAI Standard)

- Constants: `E_VARIABLE` (uppercase, `E_` prefix)
- Variables: `mos_variableName` (lowerCamelCase, `mos_` prefix)
- Methods: max 40 lines; split into helpers if longer
- Docstrings: Google style on public functions and classes
- Error handling: log with correlation ID; never log PHI
- Secrets: platform secrets manager only; see `.env.example` for non-secret placeholders
- Orchestration: **Temporal** for study lifecycle (no n8n)

## API Standards

- REST JSON under `/api/v1/...` where applicable; health at root
- OpenAPI from FastAPI automatic schema at `/docs` (dev only)
- Authentication: **SecurityClient / MSS** in production—stubs in scaffold
- Rate limiting: API gateway in production

## Section 9 — Harness 2.1 / CLAUDE.md Standard (Tier 1 annotations)

This repo follows **Harness 2.1** (`medinovai-Developer` reference: `docs/medinovai-claude-harness-2.1.md` §9).

| Harness §9 element | This repo |
|--------------------|-----------|
| Purpose + stack | Above |
| Compliance tier | **Tier 1** — full row in §Purpose |
| Dev start | `init.sh` |
| Tests | pytest paths above |
| Conventions | `E_` / `mos_` / 40-line methods |
| Tier 1 compliance block | Electronic signatures, audit logging hooks, traceability via features |
| Git branches | `main` protected; `feature/F###-description` for agents |

**Tier 1-only files:** `AUDIT_TRAIL.md`, `.claude/commands/compliance-check.md`, extended `feature_list.json` (≥60 features).

## Git Branch Strategy

- `main`: production-ready only. No direct commits from agents.
- Feature branches: `feature/F###-short-description`
- Agents commit to feature branches and open PRs.

## Known Issues / Current State

- Initial scaffold: workflows and APIs are **stubs** wired for compile/run; persistence and MSS integration are not implemented.
- Worker process: `python -m src.worker` (after `init.sh` / Temporal up).

## Last Updated

2026-03-30 — Harness 2.1 Tier 1 initializer scaffold
