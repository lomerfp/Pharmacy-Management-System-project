# SDLC Progress and Decisions

Updated: 2026-10-01

## Phase 1: Planning and feasibility — complete for initial build

**Problem.** A single pharmacy needs reliable stock, batch-expiry, purchasing, prescription, checkout, payment, audit, and reporting workflows with referential integrity and atomic transactions.

**Objectives.** Demonstrate conceptual, logical, and physical database design; 3NF; constraints; transactions; SQL reports; role-based security; and tested workflows. Deliver a runnable React/TypeScript, Django REST, MySQL/InnoDB application with source, migrations/DDL, docs, fictional seed data, and test evidence.

**Scope.** One pharmacy location; one full payment per completed sale; FEFO batch allocation; customer may be omitted for suitable OTC checkout. Excluded: payroll, hospital operations, insurance, multiple branches, e-commerce, supplier portal, payment-provider integrations, split/credit/partial payments, refunds/returns unless a separately audited reversal design is added.

**Users.** Administrator, Pharmacist/Manager, Pharmacy Technician, Cashier, Inventory Officer, Owner/Manager. Authorization is backend-enforced and least-privilege. System administration does not itself grant clinical-record access.

**Feasibility.** Technical: supported open-source stack; Django ORM and transactions suit relational business rules; MySQL row locks must be tested on MySQL. Operational: role-oriented screens and staff-created accounts. Economic: no required paid software; hosting and backups have operating costs. Schedule: implement as vertical, testable slices. Local environment currently has Node 24.19.0, npm 11.17.0, Python 3.13.7, and no Docker command; MySQL integration tests cannot be truthfully reported until MySQL is available.

**Primary risks.** Concurrent overselling/over-dispensing; incorrect timezone/expiry boundaries; unnecessary exposure of customer/prescription data; duplicate requests; platform friction for MySQL client installation on Windows; incomplete backup restoration proof. Mitigations: atomic transactions and row locks, Kampala-local business-date rules, least privilege, idempotency keys, Docker/local setup alternatives, and documented restore verification.

## Phase 2: Requirements analysis — baseline documented

Requirement IDs, acceptance criteria, use cases, roles, and tests are maintained in `docs/requirements-traceability.md` as the modules are implemented. Critical acceptance conditions: no negative or ineligible stock; exactly one matching payment per completed sale; a failed checkout changes no business records; prescription quantity cannot be over-dispensed; all sensitive operations are permission-checked and audited.

## Phase 3: System and database design — initial design documented

**Architecture.** React client -> Django REST API -> Django service/business layer -> MySQL/InnoDB. Authenticated API, server-side validation, ORM/parameterized access, and transaction boundaries are authoritative. Static/media handling and production serving are documented separately.

**Core model.** Preserve the 15 approved entities and associations from the project brief. Associative entities have independent surrogate keys. `Batch` has physical `BatchID`, plus unique `(DrugID, BatchNumber)`. Enforce one supplier per batch in this version; manufacturer-batch provenance across multiple suppliers requires a future receipt/source association extension. `Payment` is not weak. Receipts, movements, and audit history are extensions, not silent replacements for core entities.

**Design rules.** Money uses decimal fields. Timestamps are stored as UTC-aware values; business-day displays/reports use `Africa/Kampala`. A batch is expired when its expiry date is before the Kampala business date; expiry on the current local date remains eligible through that date, subject to a pharmacy policy review. FEFO sorts by expiry, then stable batch key. Cached balances/transaction prices are deliberate snapshots; balance changes are made through audited movements and transactional updates, while sale unit price is snapshotted at checkout.

## Phase 4: Implementation

| Slice | Status | Evidence |
|---|---|---|
| Workspace structure and environment | Implemented | README, `.env.example`, Compose, VS Code tasks/launch, frontend/backend source |
| Authentication, roles, permissions | Partial | JWT, account APIs, reset/change/logout, default least-privilege roles; MySQL/browser verification pending |
| Drugs, batches, suppliers, stock movements | Partial | Models/APIs, protected balances, audited reasoned adjustments; forms/quarantine UI incomplete |
| Purchase orders and receipts | Partial | Atomic creation/transitions/partial receipt/idempotency; full lists and UI incomplete |
| Customers, doctors, prescriptions | Partial | APIs, review/eligibility, checkout allowance checks; more status and MySQL concurrency cases pending |
| POS, FEFO, payments | Partial | Atomic FEFO checkout/payment, idempotency, frontend cart; receipt detail and MySQL concurrency pending |
| Dashboards, reports, exports | Partial | Live database dashboard, paginated JSON/CSV reports, audit API, reports UI; some filters/PDF remain |
| Documentation and operational verification | Partial | ERDs/DFDs, traceability, API, SQL, operations and academic outline; MySQL/restore evidence pending |

## Phase 5: Testing and quality assurance — initial slice verified

No test is marked passed until actually run. Twenty-one tests pass on the explicitly selected SQLite test configuration; frontend build, Django checks, migration consistency, and OpenAPI validation also pass. MySQL service is running, but app credentials/schema are not configured in this workspace; MySQL transaction/locking behavior remains unverified. Full results are in `docs/test-results.md`.

## Phase 6: Deployment

Production deployment, secrets, TLS, allowed hosts, static/media serving, database backups, restoration rehearsal, and migration review are required. No live deployment or production database changes are authorized by this project setup request.

Local MySQL verification is pending: the Windows `MySQL80` service is running and port 3306 responds, but no application credentials or workspace `.env` are configured. An empty-password root probe was denied. The safe local schema/account setup procedure is documented in `docs/operations.md`; once the developer supplies/configures that local app account, run migrations and repeat database tests against MySQL. No credential guessing or password reset was attempted.

## Phase 7: Maintenance and evaluation

Known limitations and future work are tracked in `docs/known-issues.md`. Review database backups, audit access, dependency updates, account deactivation, and report reconciliation routinely.

## Resume checklist

- [ ] Complete database/authentication foundation.
- [ ] Implement inventory, purchasing/receiving, prescriptions, POS/payments.
- [ ] Implement dashboards/reports/exports.
- [ ] Run automated checks and MySQL workflow/concurrency tests.
- [ ] Complete diagrams, data dictionary, API docs, user guide, and academic report.
- [ ] Verify backup and restore on a disposable development database.
