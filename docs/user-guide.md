# User Guide (Planned Workflow)

The user-facing workflows below describe intended access boundaries; only inventory/supplier and limited purchase/checkout API slices currently exist. UI modules are still placeholders.

- **Administrator:** create/deactivate staff and manage roles/settings without automatic permission to clinical information.
- **Pharmacist/Manager:** review prescriptions, manage clinical records where granted, supervise dispensing and reports.
- **Pharmacy Technician:** handle inventory and prescription tasks explicitly assigned; no implicit owner permissions.
- **Cashier:** checkout and see only minimal prescription validation/remaining-quantity information; no customer history or clinical instructions by default.
- **Inventory Officer:** manage drugs, batches, suppliers, purchase orders, receiving, movements, and reasoned adjustments as separately granted.
- **Owner/Manager:** access financial and operational reports only as configured; clinical-record access is not implied.

Once implemented, sign in with the administrator-created account, choose a module from navigation, use search/filter and pagination, and confirm any stock-affecting or irreversible action. Completed sale/payment records are immutable through ordinary edit endpoints. Keep credentials private and report suspected stock discrepancies to the authorized inventory/pharmacy manager.
