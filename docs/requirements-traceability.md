# Requirements Traceability (Initial Slice)

Statuses: Implemented means present in source; Verified means an automated check has passed. Anything else remains pending.

| ID | Requirement / acceptance | Implementation | Verification | Status |
|---|---|---|---|---|
| DB-01 | Preserve 15 approved core entities and relationships | `backend/pharmacy/models.py`, migration `0001_initial` | Migration generated; Django check clean | Implemented; no live MySQL apply |
| DB-02 | Unique batch per drug; allow same batch number across drugs | `Batch` unique constraint `(drug, batch_number)` | `test_duplicate_batch_number_is_scoped_to_drug` | Verified on SQLite; retest on MySQL |
| DB-03 | Payment is one-to-one with sale | `Payment.sale` OneToOneField | Schema migration | Implemented |
| AUTH-01 | Staff authentication and least privilege | Staff custom user, Role JSON permission keys, JWT auth, reset/change/logout endpoints, `HasRolePermission` | auth, reset, logout and role tests | Partial; MySQL and browser verification pending |
| AUTH-03 | Self-service signup without uncontrolled access | Public signup creates inactive, roleless staff request | pending signup and inactive-login tests | Verified on SQLite; email verification not included |
| AUTH-04 | Admin can assign/activate staff and remove access safely | Staff role PATCH/activation and DELETE-to-deactivation with audit | staff management lifecycle test | Verified on SQLite; MySQL pending |
| AUTH-02 | Cashier can identify a customer for prescription checkout without history access | Minimal checkout lookup with separate `sales.customer_lookup` permission | cashier minimal-field test; customer history denial test | Verified on SQLite; MySQL/API deployment pending |
| INV-01 | No direct batch balance overwrite | Batch API denies create/update/delete; only receipt and checkout services mutate balances | API implementation review | Implemented for exposed API; adjustment workflow pending |
| INV-02 | Expired stock excluded | Kampala-local date cutoff and available status in checkout queryset | expired stock rollback test | Verified on SQLite |
| BUY-01 | Purchase orders contain drug lines | PO create serializer/view and models | Django check | Partial; list/detail/report pages pending |
| BUY-02 | Receive partial deliveries; reject over-receipt | `receive_purchase_order` atomic service, extension receipt models | two receiving tests | Verified on SQLite |
| BUY-03 | Duplicate receiving requests are idempotent | Unique receipt request key | duplicate receipt test | Verified on SQLite |
| POS-01 | OTC sale may omit customer | checkout service | FEFO/anonymous OTC test | Verified on SQLite |
| POS-02 | Deterministic FEFO split allocation | eligible batches ordered expiry then id; separate SaleItem rows | FEFO split test | Verified on SQLite |
| POS-03 | Checkout and payment atomic; exact server-calculated total | checkout atomic service and one-to-one payment | checkout and expiry rollback tests | Partial; payment edge-case coverage incomplete |
| POS-04 | Duplicate checkout key cannot deduct twice | unique key reservation in atomic transaction | repeated checkout test | Verified on SQLite; MySQL concurrency pending |
| RX-01 | Prescription-only sale requires authorized matching prescription | checkout service checks reviewed status, customer, prescribed drug, remaining units | customer mismatch/excess allowance test and review API test | Partial; more status cases and MySQL concurrency pending |
| SEC-01 | API permission enforcement | role permission class and restricted inventory/supplier/sales endpoints | allowed/denied permission tests | Verified for sample API view |
| RPT-01 | Reports, exports, dashboard metrics require authorization | Dashboard, paginated JSON/CSV report API, audit route, Reports UI | dashboard reconciliation, CSV/report/audit permission tests | Partial; remaining report filters/PDF/UI pending |
| UX-01 | Responsive navigation and data-backed core screens | Login/reset, role navigation, dashboard, inventory, POS, reports | TypeScript/Vite production build | Build verified; purchasing/prescriptions/staff/settings screens remain placeholders |

## User acceptance checklist (not yet executed)

- [ ] Create admin and role-specific staff; verify staff activation/deactivation and password reset.
- [ ] Create supplier, drug and order; receive in multiple batches and verify stock ledger.
- [ ] Confirm expiry-date boundary on Kampala local day and exclude expired/quarantined/inactive stock.
- [ ] Complete anonymous OTC purchase and print its receipt.
- [ ] Review a prescription, dispense in multiple sales, and verify remaining allowance.
- [ ] Submit two concurrent checkouts for the final units against MySQL; no negative stock.
- [ ] Submit duplicate checkout and receipt requests; no duplicate stock movement/payment.
- [ ] Reconcile reports and CSV/PDF exports against completed sales and payments.
- [ ] Verify role restrictions for clinical records, exports, inventory adjustment, and audit history.
