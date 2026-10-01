# Software Requirements Specification (SRS)

Version 0.1, initial implementation baseline, updated 2026-10-01.

## Purpose and system boundary

The Pharmacy Management System supports one physical pharmacy location. Staff access a React web client and a Django REST API backed by MySQL/InnoDB. The API owns authentication, authorization, validation, calculations, and transaction safety. Suppliers and external payment providers are outside the system; non-cash methods are manually recorded only.

## User classes and least-privilege policy

Permission keys are individually configurable on Role records. The table is the intended default policy, not a hard-coded universal bundle.

| User class | Intended access |
|---|---|
| Administrator | Staff accounts, roles, operational settings; clinical records only if separately granted |
| Pharmacist/Manager | Prescription review/dispense authorization, assigned operational controls, approved reports |
| Pharmacy Technician | Assigned inventory and prescription workflow tasks; no implicit staff administration |
| Cashier | Checkout and minimum prescription eligibility/remaining quantity only; no customer history or clinical directions by default |
| Inventory Officer | Drug/category, suppliers, purchasing/receiving, batch status and reasoned adjustments |
| Owner/Manager | Financial/operational dashboards and reports as explicitly assigned; clinical access is not implied |

## Functional requirements

| ID | Requirement | Acceptance criterion |
|---|---|---|
| FR-AUTH-01 | Users can request staff access, and staff can authenticate only after approval | Signup creates an inactive roleless account; invalid/inactive credentials are rejected |
| FR-AUTH-02 | Administrators can assign roles, activate, and remove staff access | Removal deactivates instead of deleting; inactive staff cannot authenticate; audit is preserved |
| FR-AUTH-03 | Password change/reset and logout are supported | Reset token is expiring and single-use; logged-out/expired refresh credentials cannot continue a session |
| FR-AUTH-04 | API actions enforce role permissions | Denied API and export requests return a safe authorization error |
| FR-CAT-01 | Authorized staff manage categories and drugs | Required fields, decimal price, status, unit and category are validated server-side |
| FR-INV-01 | Authorized staff view batches and sellable stock | Sellable stock excludes inactive, quarantined, and expired batches |
| FR-INV-02 | Stock adjustments require permission, reason, audit, and a movement record | No ordinary endpoint can directly overwrite a balance; negative stock is impossible |
| FR-BUY-01 | Authorized staff create and transition purchase orders | Draft, ordered, partially received, received, and cancelled transitions are constrained |
| FR-BUY-02 | Receiving supports partial delivery and multiple batches | Stock increases only on receipt; receipt is traced to order, supplier, staff, and batch |
| FR-BUY-03 | Duplicate receipt submission is idempotent; over-receipt is rejected | Repeating a request key changes no quantities twice; rejected receipt leaves no partial records |
| FR-PEO-01 | Authorized staff maintain minimal customer and doctor records | Customer/prescription history is hidden from users without explicit clinical permission |
| FR-RX-01 | Staff record and pharmacist-review prescriptions | A prescription includes customer, doctor, recorder, date/reference and ordered items/instructions |
| FR-RX-02 | Prescription dispensing enforces authorized remaining quantity | Missing, mismatched, cancelled, unreviewed, or exhausted authorization prevents checkout |
| FR-POS-01 | Cashier searches drugs and submits a cart | Anonymous customer is allowed for eligible OTC sales; server recalculates all prices and totals |
| FR-POS-02 | Checkout allocates eligible batches FEFO | Expiry ascending then stable batch key; split quantity creates separate SaleItem records |
| FR-POS-03 | Checkout, stock changes, sale items, and one payment are atomic | Failure rolls all effects back; completed payment equals the server total |
| FR-POS-04 | Checkout requests support idempotency | Repeated key returns the first completed sale and does not repeat stock deduction/payment |
| FR-PAY-01 | Cash and non-cash payment methods are recordable | Cash change is not revenue; non-cash references are labeled manual and not provider-verified |
| FR-DASH-01 | Dashboard metrics use persisted completed records | Completed totals/counts and stock alerts reconcile to source rows; no fabricated figures |
| FR-RPT-01 | Reports support filters, pagination, totals, and permitted exports | Export permissions match screen permissions and financial totals reconcile to completed records |
| FR-AUD-01 | Sensitive operations are audited | Actor, event, target and safe metadata are recorded without credentials/tokens/unneeded clinical data |
| FR-SET-01 | Pharmacy name/logo/contact/receipt footer/currency/timezone/expiry thresholds are configurable | Operational setting changes are authorized and audit-recorded |
| FR-UX-01 | Staff workflows are keyboard-accessible and responsive | Focus is visible, states are explicit, tables/forms work on desktop and usable tablet widths |

## Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-SEC-01 | Use Django password hashing, server-side validation, least privilege, safe error messages, secure secret configuration, throttling, and protected CORS/CSRF/session settings. |
| NFR-DATA-01 | Use InnoDB foreign keys and constraints; money uses decimal arithmetic; transactions lock rows whose stock/allowance is contested. |
| NFR-TIME-01 | Store UTC-aware timestamps; display/report business dates in Africa/Kampala. Expiry date equal to current Kampala business date remains eligible that date. |
| NFR-AVAIL-01 | Document backup, restore, monitoring, and recovery objectives; prove restoration before production use. |
| NFR-API-01 | REST endpoints are documented with an OpenAPI schema and safe pagination/filtering. |
| NFR-TEST-01 | MySQL integration tests cover concurrency and constraints; SQLite unit tests are not evidence for row locks. |
| NFR-MAINT-01 | Separate presentation, serializers/API validation, service logic, and ORM data access; changes have migrations and requirement/test traceability. |

## Use cases

- **UC-01 Sign in:** staff submits credentials; server validates active account, issues short-lived access and refresh token, and logs safe authentication events.
- **UC-02 Maintain inventory:** inventory officer searches drug/batch, updates catalog or status; balance changes only through authorized movement services.
- **UC-03 Place and receive order:** authorized staff creates a draft with supplier/items, submits it, records one or more receipts and batches; system rejects over-receipt and recalculates outstanding quantities atomically.
- **UC-04 Review prescription:** pharmacist checks entered prescription and authorizes/cancels it; system does not recommend treatment or substitute medicines.
- **UC-05 Checkout:** cashier builds OTC/prescription cart; API validates prescription/customer, locks FEFO eligible batches, computes price/payment, and commits or rolls back as one unit.
- **UC-06 Reconcile:** authorized manager filters sales, payments, stock or purchase reports and exports only permitted data.
- **UC-07 Administer access:** administrator creates/deactivates staff and sets role permissions; clinical access remains a separate permission decision.
- **UC-08 Request staff account:** a user submits name, username, email, and password; the system creates an inactive request with no role. An administrator reviews it, assigns the least-privilege role, and activates it before login is permitted.

## Business invariants

1. Each Drug has one Category; each Batch has one Drug and one Supplier; `(DrugID, BatchNumber)` is unique.
2. Batch balance is between zero and received units; it changes only through controlled receipt/sale/adjustment services.
3. Expired, inactive, and quarantined stock is never dispensed; eligibility expiry comparison is against Kampala date.
4. SaleItem references the actual allocated Batch; FEFO allocation is deterministic.
5. Prescription-only drugs need an approved matching prescription and enough remaining authorization for its customer.
6. Completed Sale has items and one Payment for exactly its server-calculated total; draft sales may have no payment.
7. A failed or repeated checkout/receipt must not duplicate or partially apply persistent effects.
8. Completed transaction rows are immutable through normal edit/delete APIs. Returns/refunds are out of scope until audited reversals are designed.
9. All purchases and payments use UGX by default, with decimal values and timestamps stored consistently.

## Scope exclusions

Payroll, hospital management, insurance claims, branches, online medicine orders, supplier portals, payment provider integrations, split/credit/partial payments, and unaudited return/refund behavior are excluded from version one. No legal/regulatory certification is claimed.

## Traceability

See [requirements-to-implementation traceability](requirements-traceability.md) for current source links and actual verification status. Requirements marked pending are not acceptance evidence.
