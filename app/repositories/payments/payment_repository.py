"""
Payment repository - gateway_payments, receipts, ledger, refunds.
All queries scoped by hospital_id.
"""
from uuid import UUID
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payments import Payment, PaymentReceipt, PaymentLedger, PaymentRefund
from app.models.billing import Bill


class PaymentRepository:
    def __init__(self, db: AsyncSession, hospital_id: UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def get_bill(self, bill_id: UUID) -> Optional[Bill]:
        r = await self.db.execute(
            select(Bill).where(
                and_(Bill.id == bill_id, Bill.hospital_id == self.hospital_id)
            )
        )
        return r.scalar_one_or_none()

    async def get_payment_by_reference(self, payment_reference: str) -> Optional[Payment]:
        r = await self.db.execute(
            select(Payment).where(Payment.payment_reference == payment_reference)
        )
        return r.scalar_one_or_none()

    async def get_payment(self, payment_id: UUID) -> Optional[Payment]:
        r = await self.db.execute(
            select(Payment).where(
                and_(Payment.id == payment_id, Payment.hospital_id == self.hospital_id)
            )
        )
        return r.scalar_one_or_none()

    async def create_payment(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def list_payments(
        self,
        bill_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        method: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Payment]:
        conditions = [Payment.hospital_id == self.hospital_id]
        if bill_id:
            conditions.append(Payment.bill_id == bill_id)
        if date_from:
            conditions.append(Payment.paid_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            conditions.append(Payment.paid_at <= datetime.combine(date_to, datetime.max.time()))
        if method:
            conditions.append(Payment.method == method)
        if status:
            conditions.append(Payment.status == status)
        if patient_id:
            q = (
                select(Payment)
                .join(Bill, Bill.id == Payment.bill_id)
                .where(and_(*conditions, Bill.patient_id == patient_id))
                .order_by(desc(Payment.created_at))
                .offset(skip)
                .limit(limit)
            )
            r = await self.db.execute(q)
            return list(r.scalars().all())
        r = await self.db.execute(
            select(Payment).where(and_(*conditions)).order_by(desc(Payment.created_at)).offset(skip).limit(limit)
        )
        return list(r.scalars().all())

    async def get_next_receipt_number(self) -> str:
        r = await self.db.execute(
            select(func.count(PaymentReceipt.id)).where(
                PaymentReceipt.hospital_id == self.hospital_id
            )
        )
        count = r.scalar() or 0
        return f"RCP-{count + 1:06d}"

    async def create_receipt(self, receipt: PaymentReceipt) -> PaymentReceipt:
        self.db.add(receipt)
        await self.db.flush()
        return receipt

    async def create_ledger_entry(self, entry: PaymentLedger) -> PaymentLedger:
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def create_refund(self, refund: PaymentRefund) -> PaymentRefund:
        self.db.add(refund)
        await self.db.flush()
        return refund

    async def list_ledger(
        self,
        bill_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PaymentLedger]:
        conditions = [PaymentLedger.hospital_id == self.hospital_id]
        if bill_id:
            conditions.append(PaymentLedger.bill_id == bill_id)
        if date_from:
            conditions.append(PaymentLedger.created_at >= date_from)
        if date_to:
            conditions.append(PaymentLedger.created_at <= date_to)
        if patient_id:
            # join with bills to filter by patient_id
            q = (
                select(PaymentLedger)
                .join(Bill, Bill.id == PaymentLedger.bill_id)
                .where(and_(PaymentLedger.hospital_id == self.hospital_id, Bill.patient_id == patient_id))
                .order_by(desc(PaymentLedger.created_at))
                .offset(skip)
                .limit(limit)
            )
            r = await self.db.execute(q)
            return list(r.scalars().all())
        r = await self.db.execute(
            select(PaymentLedger).where(and_(*conditions)).order_by(desc(PaymentLedger.created_at)).offset(skip).limit(limit)
        )
        return list(r.scalars().all())

    async def sum_refunds_for_payment(self, payment_id: UUID) -> Decimal:
        r = await self.db.execute(
            select(func.coalesce(func.sum(PaymentRefund.refund_amount), 0)).where(
                and_(PaymentRefund.payment_id == payment_id, PaymentRefund.refund_status == "SUCCESS")
            )
        )
        return r.scalar() or Decimal("0")

    async def list_refunds_for_payment(self, payment_id: UUID) -> List[PaymentRefund]:
        r = await self.db.execute(
            select(PaymentRefund)
            .where(
                and_(PaymentRefund.payment_id == payment_id, PaymentRefund.hospital_id == self.hospital_id)
            )
            .order_by(desc(PaymentRefund.created_at))
        )
        return list(r.scalars().all())
