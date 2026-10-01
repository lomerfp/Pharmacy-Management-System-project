# REST API (Current Surface)

Base path `/api/`; JSON request/response. OpenAPI is served at `/api/schema/` and Swagger UI at `/api/docs/`. Protected endpoints use bearer JWT unless stated. JWT token creation and refresh are `/api/auth/token/` and `/api/auth/token/refresh/`. Tokens currently use Django's default username field; do not expose clinical fields in cashier interfaces.

| Method and path | Permission key | Purpose |
|---|---|---|
| `GET /api/health/` | Public | Process health only; does not prove database health |
| `POST /api/auth/token/` | Anonymous, throttled | Obtain access/refresh JWT |
| `POST /api/auth/token/refresh/` | Refresh token | Refresh JWT |
| `POST /api/auth/signup/` | Anonymous, throttled | Request staff access; creates inactive roleless account requiring admin approval |
| `GET /api/auth/me/` | Authenticated | Current staff identity and role permission keys |
| `POST /api/auth/logout/` | Authenticated | Blacklist a refresh token |
| `POST /api/auth/password/change/` | Authenticated | Change password and revoke outstanding refresh tokens |
| `POST /api/auth/password/reset/` | Anonymous, generic response | Request an expiring single-use email token |
| `POST /api/auth/password/reset/confirm/` | Anonymous, valid token | Set a new password and consume token atomically |
| `GET,POST /api/categories/` | `inventory.read` / `inventory.manage` | Category listing/maintenance |
| `GET,POST /api/drugs/` | `inventory.read` / `inventory.manage` | Drug listing/maintenance |
| `GET,POST /api/suppliers/` | `purchasing.read` / `purchasing.manage` | Supplier listing/maintenance |
| `GET,POST,PATCH,DELETE /api/staff/` | `staff.manage` | List/create/update and deactivate staff; DELETE preserves historical records |
| `GET,POST,PATCH /api/roles/` | `staff.manage` | Configure roles; roles are deactivated rather than deleted |
| `GET /api/batches/` | `inventory.read` | Batch listing; balances cannot be directly created/edited/deleted |
| `POST /api/purchase-orders/` | `purchasing.manage` | Create a draft order and item lines |
| `POST /api/purchase-orders/{id}/transition/` | `purchasing.manage` | Submit or cancel draft order |
| `POST /api/purchase-orders/{id}/receipts/` | `purchasing.receive` | Receive a partial/full delivery; require `Idempotency-Key` header |
| `POST /api/sales/checkout/` | `sales.checkout` | Atomic checkout/payment; require `Idempotency-Key` header |
| `GET /api/sales/customer-lookup/?q={text}` | `sales.customer_lookup` | Minimal customer ID/name for checkout only; no history or clinical details |
| `GET /api/sales/` | `sales.read` | Recent completed sale list |
| `GET /api/reports/{stock,batches,sales,sales-by-drug,payments,purchases,movements}/` | `reports.read` | Paginated report rows; use `?export=csv` for authorized CSV output |
| `GET /api/audit/` | `audit.read` | Paginated safe audit events |
| `POST /api/batches/{id}/adjustments/` | `inventory.adjust` | Reasoned, audited stock adjustment |
| `GET,PATCH /api/settings/` | `settings.manage` | Read and update supported pharmacy settings |
| `GET /api/prescriptions/eligible/?customer_id={id}` | `sales.checkout` | Minimum drug and remaining quantity data for checkout |
| `POST /api/prescriptions/{id}/review/` | `prescriptions.review` | Approve or cancel a pending prescription |

Inventory/list APIs use Django REST pagination/filtering defaults where applicable. Public signup creates inactive requests only: account access requires an administrator to assign a role and activate the staff record. Admin deactivation is a soft removal that retains history. Do not treat the API as production complete.

## Checkout request example

```json
{
  "customer_id": null,
  "prescription_id": null,
  "items": [{"drug_id": 1, "quantity": 2}],
  "payment_method": "cash",
  "cash_tendered": "1000.00"
}
```

The server selects active, available, non-expired batches in FEFO order (expiry then batch id), computes prices from current Drug records, creates one SaleItem per allocated batch, records exactly one payment, and performs stock deductions in one atomic service transaction. Cash tender/change are recorded separately from revenue. Other payment methods accept a manually recorded reference and are not provider verified.

## Purchase receipt request example

Send `Idempotency-Key` header and JSON:

```json
{
  "items": [{"purchase_order_item_id": 1, "quantity": 3, "batch_number": "DEMO-LOT-01", "expiry_date": "2027-06-30"}]
}
```

Received stock is added only through the service, and over-receipts are rejected. In this version a repeated drug/batch can be merged only when supplier, expiry, and status match.
