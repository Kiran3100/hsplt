# Payment Gateway Module — Reference

## 1. Schemas + Repository + PaymentService

| Component | Location | Key pieces |
|-----------|----------|------------|
| **Schemas** | `app/schemas/payments/` | `PaymentCollectRequest/Response`, `AdvancePaymentRequest/Response`, `RefundRequest/Response`, `LedgerEntryResponse`, `LedgerQuery`, `ReceiptResponse` (see `__init__.py`) |
| **Repository** | `app/repositories/payments/payment_repository.py` | `get_bill`, `get_payment_by_reference`, `get_payment`, `create_payment`, `list_payments`, `get_next_receipt_number`, `create_receipt`, `create_ledger_entry`, `create_refund`, `list_ledger`, `sum_refunds_for_payment` |
| **PaymentService** | `app/services/payments/payment_service.py` | `record_payment` (idempotent, applies to bill, ledger, receipt), `_apply_payment_to_bill`, `generate_receipt`, `process_refund`, `record_advance_payment`, `reconcile_transactions`, `handle_webhook_event` |

## 2. Provider interface + Razorpay/Stripe/Paytm + webhooks

| Component | Location |
|-----------|----------|
| **Interface** | `app/services/payments/providers/base.py` — `PaymentProviderInterface`: `create_order`, `verify_signature`, `refund_payment`, `parse_webhook_payload` |
| **Razorpay** | `app/services/payments/providers/razorpay_provider.py` |
| **Stripe** | `app/services/payments/providers/stripe_provider.py` |
| **Paytm** | `app/services/payments/providers/paytm_provider.py` |
| **Webhooks** | `app/api/v1/routers/payment_webhooks/webhooks.py` — `POST /api/v1/payments/webhooks/{provider}` (razorpay \| stripe \| paytm) |

## 3. Routers: collect, advance, refund, receipt, ledger, reports

| Route | Method | Handler (in `app/api/v1/routers/payments_gateway/collect.py`) |
|-------|--------|----------------------------------------------------------------|
| **Collect** | `POST /payments/collect` | `collect_payment` |
| **Advance** | `POST /payments/advance` | `advance_payment` |
| **Refund** | `POST /payments/{payment_id}/refund` | `refund_payment` |
| **Receipt PDF** | `GET /payments/{payment_id}/receipt/pdf` | `get_receipt_pdf` |
| **Receipt duplicate** | `POST /payments/{payment_id}/receipt/duplicate` | `duplicate_receipt` |
| **List payments** | `GET /payments` | `list_payments` |
| **Get payment** | `GET /payments/{payment_id}` | `get_payment` |
| **Ledger** | `GET /payments/ledger` | `get_ledger` |
| **Outstanding** | `GET /payments/outstanding` | `get_outstanding` |
| **Reconciliation** | `GET /payments/reports/reconciliation` | `get_reconciliation` |

Base path: `/api/v1` (from main API router). So full path e.g. `POST /api/v1/payments/collect`.
