# Known Issues and Backlog

## Incomplete before this is a usable PMS

- Replace remaining placeholders with customer, doctor, prescription, purchasing, staff, settings, and audit-history screens. Audit history API exists.
- Complete staff/role administration UI and audit browsing; auth lifecycle endpoints exist, but production reset-email transport still needs configuration.
- Expand prescription tests for missing, mismatched, cancelled, unreviewed, exhausted, and concurrent dispensing on MySQL.
- Complete drug/category/supplier forms and quarantine workflow. Batch balances are protected; reasoned, audited adjustment API exists.
- Add purchase-order list/detail/history and supplier report filters; partial receipt and over-receipt handling is implemented and tested.
- Add prescription lookup into POS, polished/printable receipt output, and visible cash tender/change details after checkout.
- Complete all report date filters, prescription history with clinical authorization, staff sales analysis, and PDF output. Current reports include sales, sales by drug, payment totals, stock, batches, purchases, and movements with CSV permission checks.
- Extend the debug-guarded fictional seed command with more terminal states and verify it against MySQL.
- Add data dictionary, full DFDs, Chen diagram at publication-ready detail, physical DDL export, complete manual/UAT guide, academic report, and presentation outline.
- Test MySQL/InnoDB transaction/locking behavior and rehearse backups/restoration.

## Current technical risks

- MySQL80 is running and port 3306 is reachable, but this workspace has no `.env`/application account. An empty-password root login was denied; do not guess credentials. MySQL migration/locking checks need the user-created local app account described in `operations.md`.
- SQLite is only a unit-test harness; it does not model InnoDB row locks.
- Current non-cash payment references are manual only; no external provider verification exists.
- Role permissions are configurable string keys and `bootstrap_roles` seeds least-privilege defaults; there is no role-permission UI yet.
- Pharmacy settings persist in the database, but not all runtime options (such as expiry horizon) dynamically consume these records yet.
- Sale/receipt number UUID suffixes are unique identifiers, not human-friendly sequential fiscal receipt numbering.
- This academic project makes no legal or regulatory compliance claim.

## Future enhancements

- Multi-supplier manufacturer-batch provenance via an explicit batch source association.
- Audited returns/refunds, only after a full reversal/stock reconciliation design.
- Provider-integrated mobile money/card payments and verified callbacks.
- Multi-branch operation only after explicit scope and inventory-location model redesign.
