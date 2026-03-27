"""
Payment Gateway service - record_payment, apply_payment_to_bill, generate_receipt, process_refund.
Does NOT live in billing service; updates bill totals via this module.
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payments import Payment, PaymentReceipt, PaymentLedger, PaymentRefund
from app.models.billing import Bill
from app.models.billing.audit import FinanceAuditLog
from app.repositories.payments.payment_repository import PaymentRepository


class PaymentServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class PaymentService:
    def __init__(self, db: AsyncSession, hospital_id: UUID, user_id: UUID):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id
        self.repo = PaymentRepository(db, hospital_id)

    def _audit(self, entity_type: str, entity_id: UUID, action: str, new_value: Optional[dict] = None):
        log = FinanceAuditLog(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            new_value=new_value,
            performed_by_user_id=self.user_id,
        )
        self.db.add(log)

    async def _get_bill(self, bill_id: UUID) -> Bill:
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise PaymentServiceError("BILL_NOT_FOUND", "Bill not found or not accessible. Ensure the bill exists and belongs to your hospital.")
        if bill.status not in ("FINALIZED", "PARTIALLY_PAID"):
            raise PaymentServiceError("BILL_NOT_FINALIZED", f"Payment can only be recorded when bill is FINALIZED or PARTIALLY_PAID (current status: {bill.status})")
        return bill

    def _apply_payment_to_bill(self, bill: Bill, amount: float) -> None:
        """Update bill amount_paid, balance_due, status."""
        bill.amount_paid = float(Decimal(str(bill.amount_paid)) + Decimal(str(amount)))
        bill.balance_due = float(Decimal(str(bill.total_amount)) - Decimal(str(bill.amount_paid)))
        if bill.balance_due <= 0:
            bill.status = "PAID"
        else:
            bill.status = "PARTIALLY_PAID"

    async def record_payment(
        self,
        bill_id: UUID,
        amount: float,
        method: str,
        idempotency_key: str,
        provider: Optional[str] = None,
        currency: str = "INR",
        transaction_id: Optional[str] = None,
        gateway_order_id: Optional[str] = None,
        gateway_signature: Optional[str] = None,
        status: str = "SUCCESS",
        metadata: Optional[dict] = None,
    ) -> Payment:
        """Validate bill finalized, prevent overpayment, create payment, update bill, ledger, receipt, audit."""
        existing = await self.repo.get_payment_by_reference(idempotency_key)
        if existing:
            return existing  # idempotent
        bill = await self._get_bill(bill_id)
        balance_due = float(bill.balance_due)
        if amount > balance_due:
            raise PaymentServiceError("PAYMENT_EXCEEDS_BALANCE", f"Amount exceeds balance due ({balance_due})")
        if amount <= 0:
            raise PaymentServiceError("INVALID_AMOUNT", "Amount must be positive")
        now = datetime.utcnow()
        payment = Payment(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            bill_id=bill_id,
            payment_reference=idempotency_key,
            method=method.upper(),
            provider=provider,
            amount=Decimal(str(amount)),
            currency=currency,
            status=status,
            transaction_id=transaction_id,
            gateway_order_id=gateway_order_id,
            gateway_signature=gateway_signature,
            collected_by_user_id=self.user_id,
            paid_at=now if status == "SUCCESS" else None,
            metadata_=metadata,
        )
        await self.repo.create_payment(payment)
        self._apply_payment_to_bill(bill, amount)
        balance_after = float(bill.balance_due)
        ledger = PaymentLedger(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            bill_id=bill_id,
            payment_id=payment.id,
            entry_type="CREDIT",
            amount=Decimal(str(amount)),
            balance_after=Decimal(str(balance_after)),
        )
        await self.repo.create_ledger_entry(ledger)
        receipt_number = await self.repo.get_next_receipt_number()
        receipt = PaymentReceipt(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            payment_id=payment.id,
            receipt_number=receipt_number,
            is_duplicate=False,
        )
        await self.repo.create_receipt(receipt)
        await self.db.flush()
        self._audit("PAYMENT", payment.id, "PAYMENT_COLLECTED", {"amount": amount, "bill_id": str(bill_id), "receipt_number": receipt_number})
        return payment

    async def generate_receipt(self, payment_id: UUID, is_duplicate: bool = False) -> PaymentReceipt:
        payment = await self.repo.get_payment(payment_id)
        if not payment:
            raise PaymentServiceError("PAYMENT_NOT_FOUND", "Payment not found")
        if is_duplicate:
            r = await self.db.execute(select(PaymentReceipt).where(PaymentReceipt.payment_id == payment_id).limit(1))
            first_receipt = r.scalar_one_or_none()
            receipt_number = (first_receipt.receipt_number + "-DUP") if first_receipt else await self.repo.get_next_receipt_number()
        else:
            receipt_number = await self.repo.get_next_receipt_number()
        receipt = PaymentReceipt(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            payment_id=payment_id,
            receipt_number=receipt_number,
            is_duplicate=is_duplicate,
        )
        await self.repo.create_receipt(receipt)
        await self.db.flush()
        self._audit("DOC", receipt.id, "RECEIPT_GENERATED", {"payment_id": str(payment_id), "is_duplicate": is_duplicate})
        return receipt

    async def process_refund(
        self,
        payment_id: UUID,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
        gateway_refund_id: Optional[str] = None,
    ) -> PaymentRefund:
        """Refund; cannot exceed paid amount; update bill balance; ledger REFUND; set payment status REFUNDED if full."""
        payment = await self.repo.get_payment(payment_id)
        if not payment:
            raise PaymentServiceError("PAYMENT_NOT_FOUND", "Payment not found")
        if payment.status == "REFUNDED":
            raise PaymentServiceError("PAYMENT_ALREADY_REFUNDED", "Payment already fully refunded")
        if payment.status != "SUCCESS":
            raise PaymentServiceError("INVALID_PAYMENT_STATUS", "Only SUCCESS payments can be refunded")
        paid = float(payment.amount)
        already_refunded = await self.repo.sum_refunds_for_payment(payment_id)
        max_refund = paid - float(already_refunded)
        if max_refund <= 0:
            raise PaymentServiceError("PAYMENT_ALREADY_REFUNDED", "No refundable amount left")
        refund_amount = amount if amount is not None else max_refund
        if refund_amount > max_refund:
            raise PaymentServiceError("REFUND_EXCEEDS_AMOUNT", f"Refund cannot exceed {max_refund}")
        if refund_amount <= 0:
            raise PaymentServiceError("INVALID_REFUND_AMOUNT", "Refund amount must be positive")
        refund = PaymentRefund(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            payment_id=payment_id,
            refund_amount=Decimal(str(refund_amount)),
            reason=reason,
            refund_status="SUCCESS",
            gateway_refund_id=gateway_refund_id,
            refunded_by_user_id=self.user_id,
        )
        await self.repo.create_refund(refund)
        bill = await self.repo.get_bill(payment.bill_id)
        if bill:
            bill.amount_paid = float(Decimal(str(bill.amount_paid)) - Decimal(str(refund_amount)))
            bill.balance_due = float(Decimal(str(bill.total_amount)) - Decimal(str(bill.amount_paid)))
            bill.status = "PARTIALLY_PAID" if bill.balance_due > 0 else "PAID"
        ledger = PaymentLedger(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            bill_id=payment.bill_id,
            payment_id=payment_id,
            entry_type="REFUND",
            amount=Decimal(str(-refund_amount)),
            balance_after=Decimal(str(bill.balance_due)) if bill else None,
        )
        await self.repo.create_ledger_entry(ledger)
        if float(already_refunded) + refund_amount >= paid - 0.01:
            payment.status = "REFUNDED"
        await self.db.flush()
        self._audit("PAYMENT", payment_id, "REFUND_ISSUED", {"refund_id": str(refund.id), "amount": refund_amount})
        return refund

    async def record_advance_payment(
        self,
        admission_id: UUID,
        amount: float,
        method: str,
        idempotency_key: str,
        currency: str = "INR",
    ) -> Payment:
        """Advance payment for IPD: find or create bill for admission, then record payment."""
        from app.models.patient import Admission
        from app.models.billing import Bill
        r = await self.db.execute(
            select(Admission).where(
                Admission.id == admission_id,
                Admission.hospital_id == self.hospital_id,
            )
        )
        admission = r.scalar_one_or_none()
        if not admission:
            raise PaymentServiceError("ADMISSION_NOT_FOUND", "Admission not found")
        r2 = await self.db.execute(
            select(Bill).where(
                Bill.admission_id == admission_id,
                Bill.hospital_id == self.hospital_id,
            ).limit(1)
        )
        bill = r2.scalar_one_or_none()
        if not bill:
            from app.services.billing.billing_service import BillingService
            billing_svc = BillingService(self.db, self.hospital_id, self.user_id)
            bill = await billing_svc.create_ipd_bill(admission.patient_id, admission_id, [], notes="Advance")
            await billing_svc.finalize_bill(bill.id)
            await self.db.flush()
        return await self.record_payment(
            bill_id=bill.id,
            amount=amount,
            method=method,
            idempotency_key=idempotency_key,
            currency=currency,
        )

    async def reconcile_transactions(self, date_from: datetime, date_to: datetime) -> dict:
        """Compare system records (stub: return system totals by method)."""
        from sqlalchemy import func
        r = await self.db.execute(
            select(Payment.method, Payment.provider, func.sum(Payment.amount).label("total")).where(
                Payment.hospital_id == self.hospital_id,
                Payment.status == "SUCCESS",
                Payment.paid_at >= date_from,
                Payment.paid_at <= date_to,
            ).group_by(Payment.method, Payment.provider)
        )
        rows = r.all()
        by_method = {}
        total = 0
        for row in rows:
            key = row.method + (f":{row.provider}" if row.provider else "")
            by_method[key] = float(row.total)
            total += float(row.total)
        return {"by_method": by_method, "total": total}

    async def handle_webhook_event(self, provider: str, payload: bytes, signature: str) -> Optional[Payment]:
        """Verify signature, parse payload, idempotent update payment status and bill."""
        from app.services.payments.providers import RazorpayProvider, StripeProvider, PaytmProvider
        providers = {"razorpay": RazorpayProvider(), "stripe": StripeProvider(), "paytm": PaytmProvider()}
        impl = providers.get(provider.lower())
        if not impl:
            return None
        if not impl.verify_signature(payload, signature):
            raise PaymentServiceError("INVALID_SIGNATURE", "Webhook signature verification failed")
        data = impl.parse_webhook_payload(payload)
        payment_ref = data.get("payment_id") or data.get("order_id")
        if not payment_ref:
            return None
        # Find by gateway_order_id or payment_reference
        r = await self.db.execute(
            select(Payment).where(
                (Payment.gateway_order_id == payment_ref) | (Payment.payment_reference == payment_ref) | (Payment.transaction_id == payment_ref)
            )
        )
        payment = r.scalar_one_or_none()
        if not payment or str(payment.hospital_id) != str(self.hospital_id):
            return None
        if payment.status == "SUCCESS":
            return payment  # idempotent
        new_status = "SUCCESS" if (data.get("status") or "").upper() in ("SUCCESS", "SUCCEEDED", "TXN_SUCCESS", "CAPTURED") else "FAILED"
        payment.status = new_status
        if new_status == "SUCCESS" and not payment.paid_at:
            payment.paid_at = datetime.utcnow()
            bill = await self.repo.get_bill(payment.bill_id)
            if bill:
                self._apply_payment_to_bill(bill, float(payment.amount))
                balance_after = float(bill.balance_due)
            else:
                balance_after = 0
            ledger = PaymentLedger(
                id=uuid.uuid4(),
                hospital_id=self.hospital_id,
                bill_id=payment.bill_id,
                payment_id=payment.id,
                entry_type="CREDIT",
                amount=payment.amount,
                balance_after=Decimal(str(balance_after)),
            )
            await self.repo.create_ledger_entry(ledger)
            receipt_number = await self.repo.get_next_receipt_number()
            receipt = PaymentReceipt(
                id=uuid.uuid4(),
                hospital_id=self.hospital_id,
                payment_id=payment.id,
                receipt_number=receipt_number,
                is_duplicate=False,
            )
            await self.repo.create_receipt(receipt)
        await self.db.flush()
        self._audit("PAYMENT", payment.id, "PAYMENT_COLLECTED" if new_status == "SUCCESS" else "PAYMENT_FAILED", {"status": new_status})
        return payment
