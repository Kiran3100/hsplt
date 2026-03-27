"""
Billing repository - DB operations for service items, tax profiles, bills, payments, etc.
All queries scoped by hospital_id.
"""
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import (
    ServiceItem, TaxProfile, Bill, BillItem, IPDCharge,
    BillingPayment, Refund, FinancialDocument, InsuranceClaim, Reconciliation, FinanceAuditLog,
)
from app.models.patient import PatientProfile, Appointment, Admission


class BillingRepository:
    def __init__(self, db: AsyncSession, hospital_id: UUID):
        self.db = db
        self.hospital_id = hospital_id

    # ---------- Tax profiles ----------
    async def get_tax_profile(self, tax_id: UUID) -> Optional[TaxProfile]:
        r = await self.db.execute(
            select(TaxProfile).where(
                and_(TaxProfile.id == tax_id, TaxProfile.hospital_id == self.hospital_id)
            )
        )
        return r.scalar_one_or_none()

    async def list_tax_profiles(self, active_only: bool = True) -> List[TaxProfile]:
        conditions = [TaxProfile.hospital_id == self.hospital_id]
        if active_only:
            conditions.append(TaxProfile.is_active == True)
        r = await self.db.execute(
            select(TaxProfile).where(and_(*conditions)).order_by(asc(TaxProfile.name))
        )
        return list(r.scalars().all())

    async def create_tax_profile(self, t: TaxProfile) -> TaxProfile:
        self.db.add(t)
        await self.db.flush()
        return t

    # ---------- Service items ----------
    async def get_service_item(self, service_id: UUID) -> Optional[ServiceItem]:
        r = await self.db.execute(
            select(ServiceItem).where(
                and_(ServiceItem.id == service_id, ServiceItem.hospital_id == self.hospital_id)
            )
        )
        return r.scalar_one_or_none()

    async def get_service_item_by_code(self, code: str) -> Optional[ServiceItem]:
        r = await self.db.execute(
            select(ServiceItem).where(
                and_(ServiceItem.hospital_id == self.hospital_id, ServiceItem.code == code)
            )
        )
        return r.scalar_one_or_none()

    async def list_service_items(
        self,
        department_id: Optional[UUID] = None,
        category: Optional[str] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ServiceItem]:
        conditions = [ServiceItem.hospital_id == self.hospital_id]
        if department_id:
            conditions.append(ServiceItem.department_id == department_id)
        if category:
            conditions.append(ServiceItem.category == category)
        if active_only:
            conditions.append(ServiceItem.is_active == True)
        r = await self.db.execute(
            select(ServiceItem).where(and_(*conditions)).order_by(asc(ServiceItem.code)).offset(skip).limit(limit)
        )
        return list(r.scalars().all())

    async def get_next_bill_number(self, bill_type: str) -> str:
        """Next bill number per hospital (e.g. OPD-00001)."""
        r = await self.db.execute(
            select(func.count(Bill.id)).where(
                and_(Bill.hospital_id == self.hospital_id, Bill.bill_type == bill_type)
            )
        )
        count = r.scalar() or 0
        prefix = "OPD" if bill_type == "OPD" else "IPD"
        return f"{prefix}-{count + 1:05d}"

    async def create_bill(self, bill: Bill) -> Bill:
        self.db.add(bill)
        await self.db.flush()
        return bill

    async def get_bill(self, bill_id: UUID, load_items: bool = True) -> Optional[Bill]:
        q = select(Bill).where(
            and_(Bill.id == bill_id, Bill.hospital_id == self.hospital_id)
        )
        if load_items:
            q = q.options(
                selectinload(Bill.items),
                selectinload(Bill.patient),
                selectinload(Bill.appointment),
                selectinload(Bill.admission),
            )
        r = await self.db.execute(q)
        return r.scalar_one_or_none()

    async def get_bill_by_number(self, bill_number: str) -> Optional[Bill]:
        r = await self.db.execute(
            select(Bill).where(
                and_(Bill.hospital_id == self.hospital_id, Bill.bill_number == bill_number)
            )
        )
        return r.scalar_one_or_none()

    async def list_bills(
        self,
        status: Optional[str] = None,
        patient_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        bill_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Bill], int]:
        conditions = [Bill.hospital_id == self.hospital_id]
        if status:
            conditions.append(Bill.status == status)
        if patient_id:
            conditions.append(Bill.patient_id == patient_id)
        if date_from:
            conditions.append(Bill.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            conditions.append(Bill.created_at <= datetime.combine(date_to, datetime.max.time()))
        if bill_type:
            conditions.append(Bill.bill_type == bill_type)
        # Eager-load items, patient, appointment, admission for serialization (patient_ref, appointment_ref, admission_ref)
        base = (
            select(Bill)
            .options(
                selectinload(Bill.items),
                selectinload(Bill.patient),
                selectinload(Bill.appointment),
                selectinload(Bill.admission),
            )
            .where(and_(*conditions))
            .order_by(desc(Bill.created_at))
        )
        count_r = await self.db.execute(select(func.count(Bill.id)).where(and_(*conditions)))
        total = count_r.scalar() or 0
        r = await self.db.execute(base.offset(skip).limit(limit))
        return list(r.scalars().all()), total

    async def get_payment_by_ref(self, payment_ref: str) -> Optional[BillingPayment]:
        r = await self.db.execute(
            select(BillingPayment).where(BillingPayment.payment_ref == payment_ref)
        )
        return r.scalar_one_or_none()

    async def create_payment(self, p: BillingPayment) -> BillingPayment:
        self.db.add(p)
        await self.db.flush()
        return p

    async def get_payment(self, payment_id: UUID) -> Optional[BillingPayment]:
        r = await self.db.execute(
            select(BillingPayment).where(
                and_(BillingPayment.id == payment_id, BillingPayment.hospital_id == self.hospital_id)
            )
        )
        return r.scalar_one_or_none()

    async def list_payments(
        self,
        bill_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        method: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[BillingPayment]:
        conditions = [BillingPayment.hospital_id == self.hospital_id]
        if bill_id:
            conditions.append(BillingPayment.bill_id == bill_id)
        if date_from:
            conditions.append(BillingPayment.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            conditions.append(BillingPayment.created_at <= datetime.combine(date_to, datetime.max.time()))
        if method:
            conditions.append(BillingPayment.method == method)
        r = await self.db.execute(
            select(BillingPayment).where(and_(*conditions)).order_by(desc(BillingPayment.created_at)).offset(skip).limit(limit)
        )
        return list(r.scalars().all())

    async def create_financial_document(self, doc: FinancialDocument) -> FinancialDocument:
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def get_next_doc_number(self, doc_type: str) -> str:
        r = await self.db.execute(
            select(func.count(FinancialDocument.id)).where(
                and_(FinancialDocument.hospital_id == self.hospital_id, FinancialDocument.doc_type == doc_type)
            )
        )
        count = r.scalar() or 0
        return f"{doc_type[:2].upper()}-{count + 1:05d}"

    async def create_insurance_claim(self, c: InsuranceClaim) -> InsuranceClaim:
        self.db.add(c)
        await self.db.flush()
        return c

    async def get_insurance_claim(self, claim_id: UUID) -> Optional[InsuranceClaim]:
        r = await self.db.execute(
            select(InsuranceClaim).where(
                and_(InsuranceClaim.id == claim_id, InsuranceClaim.hospital_id == self.hospital_id)
            )
        )
        return r.scalar_one_or_none()

    async def list_insurance_claims(
        self,
        status: Optional[str] = None,
        bill_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[InsuranceClaim]:
        conditions = [InsuranceClaim.hospital_id == self.hospital_id]
        if status:
            conditions.append(InsuranceClaim.status == status)
        if bill_id:
            conditions.append(InsuranceClaim.bill_id == bill_id)
        if patient_id:
            conditions.append(InsuranceClaim.patient_id == patient_id)
        r = await self.db.execute(
            select(InsuranceClaim).where(and_(*conditions)).order_by(desc(InsuranceClaim.created_at)).offset(skip).limit(limit)
        )
        return list(r.scalars().all())

    async def create_reconciliation(self, rec: Reconciliation) -> Reconciliation:
        self.db.add(rec)
        await self.db.flush()
        return rec

    async def get_reconciliation(self, recon_id: UUID) -> Optional[Reconciliation]:
        r = await self.db.execute(
            select(Reconciliation).where(
                and_(Reconciliation.id == recon_id, Reconciliation.hospital_id == self.hospital_id)
            )
        )
        return r.scalar_one_or_none()

    async def get_reconciliation_by_date(self, recon_date: date) -> Optional[Reconciliation]:
        r = await self.db.execute(
            select(Reconciliation).where(
                and_(Reconciliation.hospital_id == self.hospital_id, Reconciliation.recon_date == recon_date)
            )
        )
        return r.scalar_one_or_none()

    async def create_audit_log(self, log: FinanceAuditLog) -> FinanceAuditLog:
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_audit_logs(
        self,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[FinanceAuditLog]:
        conditions = [FinanceAuditLog.hospital_id == self.hospital_id]
        if entity_type:
            conditions.append(FinanceAuditLog.entity_type == entity_type)
        if action:
            conditions.append(FinanceAuditLog.action == action)
        if date_from:
            conditions.append(FinanceAuditLog.performed_at >= date_from)
        if date_to:
            conditions.append(FinanceAuditLog.performed_at <= date_to)
        r = await self.db.execute(
            select(FinanceAuditLog).where(and_(*conditions)).order_by(desc(FinanceAuditLog.performed_at)).offset(skip).limit(limit)
        )
        return list(r.scalars().all())

    async def add_bill_item(self, item: BillItem) -> BillItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def delete_bill_item(self, item: BillItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def get_bill_item(self, bill_id: UUID, item_id: UUID) -> Optional[BillItem]:
        r = await self.db.execute(
            select(BillItem).where(
                and_(BillItem.id == item_id, BillItem.bill_id == bill_id)
            )
        )
        return r.scalar_one_or_none()

    # ---------- Refunds ----------
    async def create_refund(self, refund: Refund) -> Refund:
        self.db.add(refund)
        await self.db.flush()
        return refund

    async def list_refunds_by_payment(self, payment_id: UUID) -> List[Refund]:
        r = await self.db.execute(
            select(Refund).where(
                and_(Refund.hospital_id == self.hospital_id, Refund.payment_id == payment_id)
            ).order_by(desc(Refund.created_at))
        )
        return list(r.scalars().all())
