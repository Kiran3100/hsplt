"""
Billing service - business logic for bills, payments, reconciliation, audit.
Implements: calculate_bill_totals, finalize_bill_transaction, record_payment_and_update_bill, etc.
"""
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any
import uuid

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import (
    ServiceItem, TaxProfile, Bill, BillItem, IPDCharge,
    BillingPayment, Refund, FinancialDocument, InsuranceClaim, Reconciliation, FinanceAuditLog,
)
from app.repositories.billing.billing_repository import BillingRepository
from app.core.exceptions import BusinessLogicError


# Error codes per SOW
BILL_NOT_FOUND = "BILL_NOT_FOUND"
BILL_NOT_FINALIZED = "BILL_NOT_FINALIZED"
CROSS_TENANT_ACCESS_DENIED = "CROSS_TENANT_ACCESS_DENIED"
PAYMENT_EXCEEDS_BALANCE = "PAYMENT_EXCEEDS_BALANCE"
DISCOUNT_REQUIRES_APPROVAL = "DISCOUNT_REQUIRES_APPROVAL"
PAYMENT_REF_DUPLICATE = "PAYMENT_REF_DUPLICATE"
SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
PAYMENT_ALREADY_REFUNDED = "PAYMENT_ALREADY_REFUNDED"
REFUND_EXCEEDS_PAYMENT = "REFUND_EXCEEDS_PAYMENT"
BILL_ALREADY_FINALIZED = "BILL_ALREADY_FINALIZED"
BILL_CANCELLED = "BILL_CANCELLED"
BILL_REOPEN_NOT_ALLOWED = "BILL_REOPEN_NOT_ALLOWED"

# Config: discount above this (percent of total or absolute) may require approval
DISCOUNT_APPROVAL_THRESHOLD_PERCENT = 10.0
DISCOUNT_APPROVAL_THRESHOLD_AMOUNT = 500.0


class BillingService:
    def __init__(self, db: AsyncSession, hospital_id: UUID, user_id: UUID):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id
        self.repo = BillingRepository(db, hospital_id)

    def _audit(self, entity_type: str, entity_id: UUID, action: str, old_value: Optional[dict] = None, new_value: Optional[dict] = None, ip_address: Optional[str] = None):
        """Write finance audit log (fire-and-forget; caller should commit)."""
        log = FinanceAuditLog(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            performed_by_user_id=self.user_id,
            ip_address=ip_address,
        )
        self.db.add(log)

    @staticmethod
    def calculate_line_totals(quantity: float, unit_price: float, tax_percentage: float) -> tuple:
        """Returns (line_subtotal, line_tax, line_total)."""
        subtotal = Decimal(str(quantity)) * Decimal(str(unit_price))
        tax = (subtotal * Decimal(str(tax_percentage)) / Decimal("100")).quantize(Decimal("0.01"))
        total = subtotal + tax
        return float(subtotal), float(tax), float(total)

    def calculate_bill_totals(self, bill: Bill, items: Optional[List[BillItem]] = None) -> None:
        """
        Recalculate bill subtotal, tax_amount, total_amount, balance_due from items and discount.

        IMPORTANT: This helper must NOT trigger async lazy-loads (to avoid MissingGreenlet),
        so callers should either:
        - pass an explicit list of items, OR
        - ensure bill.items has already been eagerly loaded.
        """
        # Use explicitly provided items if given; otherwise use already-loaded relationship
        if items is None:
            # Access underlying dict to avoid triggering lazy load if not already present
            items = bill.__dict__.get("items") or []
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        for it in items:
            subtotal += Decimal(str(it.line_subtotal))
            tax_total += Decimal(str(it.line_tax))
        discount = Decimal(str(bill.discount_amount))
        bill.subtotal = float(subtotal)
        bill.tax_amount = float(tax_total)
        bill.total_amount = float(subtotal + tax_total - discount)
        bill.balance_due = float(Decimal(str(bill.total_amount)) - Decimal(str(bill.amount_paid)))

    async def create_tax_profile(self, name: str, gst_percentage: float, is_active: bool = True) -> TaxProfile:
        t = TaxProfile(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            name=name,
            gst_percentage=Decimal(str(gst_percentage)),
            is_active=is_active,
        )
        return await self.repo.create_tax_profile(t)

    async def update_tax_profile(self, tax_id: UUID, **kwargs) -> TaxProfile:
        t = await self.repo.get_tax_profile(tax_id)
        if not t:
            raise BusinessLogicError("Tax profile not found", [SERVICE_NOT_FOUND])
        for k, v in kwargs.items():
            if v is not None and hasattr(t, k):
                setattr(t, k, Decimal(str(v)) if k == "gst_percentage" else v)
        await self.db.flush()
        return t

    async def create_service_item(
        self,
        code: str,
        name: str,
        category: str,
        base_price: float,
        department_id: Optional[UUID] = None,
        tax_profile_id: Optional[UUID] = None,
        is_active: bool = True,
    ) -> ServiceItem:
        existing = await self.repo.get_service_item_by_code(code)
        if existing:
            raise BusinessLogicError(f"Service code already exists: {code}", ["DUPLICATE_CODE"])
        tax_pct = Decimal("0")
        if tax_profile_id:
            tp = await self.repo.get_tax_profile(tax_profile_id)
            if tp:
                tax_pct = tp.gst_percentage
        s = ServiceItem(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            department_id=department_id,
            code=code,
            name=name,
            category=category,
            base_price=Decimal(str(base_price)),
            tax_profile_id=tax_profile_id,
            is_active=is_active,
        )
        self.db.add(s)
        await self.db.flush()
        return s

    async def update_service_item(self, service_id: UUID, **kwargs) -> ServiceItem:
        s = await self.repo.get_service_item(service_id)
        if not s:
            raise BusinessLogicError("Service item not found", [SERVICE_NOT_FOUND])
        for k, v in kwargs.items():
            if v is not None and hasattr(s, k):
                setattr(s, k, Decimal(str(v)) if k == "base_price" else v)
        await self.db.flush()
        return s

    async def create_opd_bill(
        self,
        patient_id: UUID,
        appointment_id: Optional[UUID],
        items: List[dict],
        notes: Optional[str] = None,
    ) -> Bill:
        """Create OPD bill (DRAFT) with items. items: list of {service_item_id?, description, quantity, unit_price, tax_percentage?}."""
        bill_number = await self.repo.get_next_bill_number("OPD")
        bill = Bill(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            bill_number=bill_number,
            bill_type="OPD",
            patient_id=patient_id,
            appointment_id=appointment_id,
            admission_id=None,
            status="DRAFT",
            subtotal=0,
            discount_amount=0,
            tax_amount=0,
            total_amount=0,
            amount_paid=0,
            balance_due=0,
            created_by_user_id=self.user_id,
            notes=notes,
        )
        await self.repo.create_bill(bill)
        created_items: List[BillItem] = []
        for i, row in enumerate(items):
            service_item_id = row.get("service_item_id")
            description = row.get("description", "")
            quantity = float(row.get("quantity", 1))
            unit_price = float(row.get("unit_price", 0))
            tax_percentage = float(row.get("tax_percentage", 0))
            if service_item_id:
                svc = await self.repo.get_service_item(service_item_id)
                if not svc:
                    raise BusinessLogicError(f"Service item not found: {service_item_id}", [SERVICE_NOT_FOUND])
                description = description or svc.name
                if not row.get("unit_price"):
                    unit_price = float(svc.base_price)
                if not row.get("tax_percentage") and svc.tax_profile_id:
                    tp = await self.repo.get_tax_profile(svc.tax_profile_id)
                    if tp:
                        tax_percentage = float(tp.gst_percentage)
            line_subtotal, line_tax, line_total = self.calculate_line_totals(quantity, unit_price, tax_percentage)
            item = BillItem(
                id=uuid.uuid4(),
                bill_id=bill.id,
                service_item_id=service_item_id,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                tax_percentage=tax_percentage,
                line_subtotal=line_subtotal,
                line_tax=line_tax,
                line_total=line_total,
            )
            await self.repo.add_bill_item(item)
            created_items.append(item)
        await self.db.refresh(bill)
        # Use in-memory created_items to avoid async lazy-load inside calculator
        self.calculate_bill_totals(bill, created_items)
        await self.db.flush()
        self._audit("BILL", bill.id, "CREATE", new_value={"bill_number": bill.bill_number, "status": "DRAFT"})
        return bill

    async def create_ipd_bill(
        self,
        patient_id: UUID,
        admission_id: UUID,
        items: List[dict],
        notes: Optional[str] = None,
    ) -> Bill:
        """Create IPD bill (DRAFT)."""
        bill_number = await self.repo.get_next_bill_number("IPD")
        bill = Bill(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            bill_number=bill_number,
            bill_type="IPD",
            patient_id=patient_id,
            appointment_id=None,
            admission_id=admission_id,
            status="DRAFT",
            subtotal=0,
            discount_amount=0,
            tax_amount=0,
            total_amount=0,
            amount_paid=0,
            balance_due=0,
            created_by_user_id=self.user_id,
            notes=notes,
        )
        await self.repo.create_bill(bill)
        created_items: List[BillItem] = []
        for row in items:
            service_item_id = row.get("service_item_id")
            description = row.get("description", "")
            quantity = float(row.get("quantity", 1))
            unit_price = float(row.get("unit_price", 0))
            tax_percentage = float(row.get("tax_percentage", 0))
            if service_item_id:
                svc = await self.repo.get_service_item(service_item_id)
                if not svc:
                    raise BusinessLogicError(f"Service item not found: {service_item_id}", [SERVICE_NOT_FOUND])
                description = description or svc.name
                if not row.get("unit_price"):
                    unit_price = float(svc.base_price)
                if not row.get("tax_percentage") and svc.tax_profile_id:
                    tp = await self.repo.get_tax_profile(svc.tax_profile_id)
                    if tp:
                        tax_percentage = float(tp.gst_percentage)
            line_subtotal, line_tax, line_total = self.calculate_line_totals(quantity, unit_price, tax_percentage)
            item = BillItem(
                id=uuid.uuid4(),
                bill_id=bill.id,
                service_item_id=service_item_id,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                tax_percentage=tax_percentage,
                line_subtotal=line_subtotal,
                line_tax=line_tax,
                line_total=line_total,
            )
            await self.repo.add_bill_item(item)
            created_items.append(item)
        await self.db.refresh(bill)
        # Use in-memory created_items to avoid async lazy-load inside calculator
        self.calculate_bill_totals(bill, created_items)
        await self.db.flush()
        self._audit("BILL", bill.id, "CREATE", new_value={"bill_number": bill.bill_number, "status": "DRAFT"})
        return bill

    async def add_bill_items(self, bill_id: UUID, items: List[dict]) -> Bill:
        """Add line items to DRAFT bill."""
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if bill.status != "DRAFT":
            raise BusinessLogicError("Can only add items to DRAFT bill", [BILL_ALREADY_FINALIZED])
        for row in items:
            service_item_id = row.get("service_item_id")
            description = row.get("description", "")
            quantity = float(row.get("quantity", 1))
            unit_price = float(row.get("unit_price", 0))
            tax_percentage = float(row.get("tax_percentage", 0))
            if service_item_id:
                svc = await self.repo.get_service_item(service_item_id)
                if not svc:
                    raise BusinessLogicError(f"Service item not found: {service_item_id}", [SERVICE_NOT_FOUND])
                description = description or svc.name
                if not row.get("unit_price"):
                    unit_price = float(svc.base_price)
                if not row.get("tax_percentage") and svc.tax_profile_id:
                    tp = await self.repo.get_tax_profile(svc.tax_profile_id)
                    if tp:
                        tax_percentage = float(tp.gst_percentage)
            line_subtotal, line_tax, line_total = self.calculate_line_totals(quantity, unit_price, tax_percentage)
            item = BillItem(
                id=uuid.uuid4(),
                bill_id=bill_id,
                service_item_id=service_item_id,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                tax_percentage=tax_percentage,
                line_subtotal=line_subtotal,
                line_tax=line_tax,
                line_total=line_total,
            )
            await self.repo.add_bill_item(item)
        await self.db.refresh(bill)
        self.calculate_bill_totals(bill)
        await self.db.flush()
        return bill

    async def remove_bill_item(self, bill_id: UUID, item_id: UUID) -> Bill:
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if bill.status != "DRAFT":
            raise BusinessLogicError("Can only remove items from DRAFT bill", [BILL_ALREADY_FINALIZED])
        item = await self.repo.get_bill_item(bill_id, item_id)
        if not item:
            raise BusinessLogicError("Bill item not found", ["BILL_ITEM_NOT_FOUND"])
        await self.repo.delete_bill_item(item)
        await self.db.refresh(bill)
        self.calculate_bill_totals(bill)
        await self.db.flush()
        return bill

    async def apply_discount(self, bill_id: UUID, discount_amount: float, require_approval_if_over_threshold: bool = True) -> Bill:
        """Apply discount; if over threshold, set discount_approval_required (admin must approve)."""
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if bill.status != "DRAFT":
            raise BusinessLogicError("Can only apply discount to DRAFT bill", [BILL_ALREADY_FINALIZED])
        total = float(bill.total_amount)
        threshold_pct = total * (DISCOUNT_APPROVAL_THRESHOLD_PERCENT / 100)
        if require_approval_if_over_threshold and (discount_amount >= DISCOUNT_APPROVAL_THRESHOLD_AMOUNT or discount_amount >= threshold_pct):
            bill.discount_amount = discount_amount
            bill.discount_approval_required = True
            self.calculate_bill_totals(bill)
            await self.db.flush()
            self._audit("BILL", bill.id, "DISCOUNT_APPLY", new_value={"discount_amount": discount_amount, "approval_required": True})
            raise BusinessLogicError("Discount requires Hospital Admin approval", [DISCOUNT_REQUIRES_APPROVAL])
        bill.discount_amount = discount_amount
        bill.discount_approval_required = False
        self.calculate_bill_totals(bill)
        await self.db.flush()
        self._audit("BILL", bill.id, "DISCOUNT_APPLY", new_value={"discount_amount": discount_amount})
        return bill

    async def approve_discount(self, bill_id: UUID) -> Bill:
        """Hospital Admin approves discount."""
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if not bill.discount_approval_required:
            raise BusinessLogicError("No discount approval pending", ["NO_APPROVAL_PENDING"])
        bill.discount_approval_required = False
        bill.discount_approved_by_user_id = self.user_id
        self.calculate_bill_totals(bill)
        await self.db.flush()
        self._audit("BILL", bill.id, "APPROVE", new_value={"discount_approved": True})
        return bill

    async def finalize_bill(self, bill_id: UUID) -> Bill:
        """Finalize bill (DRAFT -> FINALIZED). After this, items cannot be edited."""
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if bill.status != "DRAFT":
            raise BusinessLogicError("Only DRAFT bills can be finalized", [BILL_ALREADY_FINALIZED])
        if bill.discount_approval_required:
            raise BusinessLogicError("Discount must be approved before finalizing", [DISCOUNT_REQUIRES_APPROVAL])
        from datetime import datetime as dt
        bill.status = "FINALIZED"
        bill.finalized_by_user_id = self.user_id
        bill.finalized_at = dt.utcnow()
        await self.db.flush()
        self._audit("BILL", bill.id, "FINALIZE", old_value={"status": "DRAFT"}, new_value={"status": "FINALIZED"})
        return bill

    async def cancel_bill(self, bill_id: UUID, reason: Optional[str] = None) -> Bill:
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if bill.status == "PAID":
            raise BusinessLogicError("Cannot cancel PAID bill", [BILL_ALREADY_FINALIZED])
        old_status = bill.status
        bill.status = "CANCELLED"
        if reason:
            bill.notes = (bill.notes or "") + f"\nCancel reason: {reason}"
        await self.db.flush()
        self._audit("BILL", bill.id, "CANCEL", old_value={"status": old_status}, new_value={"status": "CANCELLED"})
        return bill

    async def reopen_bill(self, bill_id: UUID, reason: Optional[str] = None) -> Bill:
        """Reopen a finalized/partially-paid bill for corrections (-> DRAFT)."""
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if bill.status not in ("FINALIZED", "PARTIALLY_PAID"):
            raise BusinessLogicError("Only FINALIZED/PARTIALLY_PAID bills can be reopened", [BILL_REOPEN_NOT_ALLOWED])
        old_status = bill.status
        bill.status = "DRAFT"
        if reason:
            bill.notes = (bill.notes or "") + f"\nReopened: {reason}"
        await self.db.flush()
        self._audit("BILL", bill.id, "REOPEN", old_value={"status": old_status}, new_value={"status": "DRAFT"})
        return bill

    async def record_payment(
        self,
        bill_id: UUID,
        amount: float,
        method: str,
        idempotency_key: str,
        provider: Optional[str] = None,
        gateway_transaction_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> BillingPayment:
        """Record payment against FINALIZED bill. Idempotent by idempotency_key (payment_ref)."""
        existing = await self.repo.get_payment_by_ref(idempotency_key)
        if existing:
            return existing  # idempotency
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if bill.status not in ("FINALIZED", "PARTIALLY_PAID"):
            raise BusinessLogicError("Payments only allowed for FINALIZED or PARTIALLY_PAID bills", [BILL_NOT_FINALIZED])
        balance = float(bill.balance_due)
        if amount > balance:
            raise BusinessLogicError("Payment exceeds balance due", [PAYMENT_EXCEEDS_BALANCE])
        from datetime import datetime as dt
        payment = BillingPayment(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            bill_id=bill_id,
            payment_ref=idempotency_key,
            method=method,
            provider=provider,
            amount=Decimal(str(amount)),
            status="SUCCESS",
            paid_at=dt.utcnow(),
            collected_by_user_id=self.user_id,
            gateway_transaction_id=gateway_transaction_id,
            extra_data=metadata,
        )
        await self.repo.create_payment(payment)
        bill.amount_paid = float(Decimal(str(bill.amount_paid)) + Decimal(str(amount)))
        bill.balance_due = float(Decimal(str(bill.total_amount)) - Decimal(str(bill.amount_paid)))
        bill.status = "PAID" if bill.balance_due <= 0 else "PARTIALLY_PAID"
        await self.db.flush()
        self._audit("PAYMENT", payment.id, "CREATE", new_value={"amount": amount, "bill_id": str(bill_id)})
        return payment

    async def update_bill_item(
        self,
        bill_id: UUID,
        item_id: UUID,
        description: Optional[str] = None,
        quantity: Optional[float] = None,
        unit_price: Optional[float] = None,
        tax_percentage: Optional[float] = None,
    ) -> Bill:
        """Update a bill item (qty/price/tax/description) and recalc totals. Only for DRAFT bills."""
        bill = await self.repo.get_bill(bill_id)
        if not bill:
            raise BusinessLogicError("Bill not found", [BILL_NOT_FOUND])
        if bill.status != "DRAFT":
            raise BusinessLogicError("Only DRAFT bills can be edited", [BILL_ALREADY_FINALIZED])
        item = await self.repo.get_bill_item(bill_id, item_id)
        if not item:
            raise BusinessLogicError("Bill item not found", ["BILL_ITEM_NOT_FOUND"])
        # Apply changes
        if description is not None:
            item.description = description
        current_qty = float(item.quantity)
        current_price = float(item.unit_price)
        current_tax = float(item.tax_percentage)
        q = float(quantity) if quantity is not None else current_qty
        p = float(unit_price) if unit_price is not None else current_price
        t = float(tax_percentage) if tax_percentage is not None else current_tax
        # Recalculate line values
        line_subtotal, line_tax, line_total = self.calculate_line_totals(q, p, t)
        from decimal import Decimal as D
        item.quantity = D(str(q))
        item.unit_price = D(str(p))
        item.tax_percentage = D(str(t))
        item.line_subtotal = D(str(line_subtotal))
        item.line_tax = D(str(line_tax))
        item.line_total = D(str(line_total))
        # Recalculate bill totals
        self.calculate_bill_totals(bill)
        await self.db.flush()
        self._audit("BILL", bill.id, "UPDATE_ITEM", new_value={"item_id": str(item.id)})
        return bill

    async def process_refund(
        self,
        payment_id: UUID,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
        gateway_refund_id: Optional[str] = None,
    ) -> Refund:
        """Process refund (full or partial). If amount is None, full refund. Updates bill amount_paid and balance_due."""
        payment = await self.repo.get_payment(payment_id)
        if not payment:
            raise BusinessLogicError("Payment not found", [PAYMENT_NOT_FOUND])
        if payment.status == "REFUNDED":
            raise BusinessLogicError("Payment already fully refunded", [PAYMENT_ALREADY_REFUNDED])
        if payment.status != "SUCCESS":
            raise BusinessLogicError("Only SUCCESS payments can be refunded", ["INVALID_PAYMENT_STATUS"])
        payment_amount = float(payment.amount)
        existing_refunds = await self.repo.list_refunds_by_payment(payment_id)
        already_refunded = sum(float(r.amount) for r in existing_refunds)
        max_refund = payment_amount - already_refunded
        if max_refund <= 0:
            raise BusinessLogicError("Payment already fully refunded", [PAYMENT_ALREADY_REFUNDED])
        refund_amount = amount if amount is not None else max_refund
        if refund_amount > max_refund:
            raise BusinessLogicError(f"Refund exceeds refundable amount (max {max_refund})", [REFUND_EXCEEDS_PAYMENT])
        if refund_amount <= 0:
            raise BusinessLogicError("Refund amount must be positive", ["INVALID_REFUND_AMOUNT"])
        from datetime import datetime as dt
        refund = Refund(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            payment_id=payment_id,
            amount=Decimal(str(refund_amount)),
            reason=reason,
            status="SUCCESS",
            refunded_at=dt.utcnow(),
            refunded_by_user_id=self.user_id,
            gateway_refund_id=gateway_refund_id,
        )
        await self.repo.create_refund(refund)
        bill = await self.repo.get_bill(payment.bill_id)
        if bill:
            bill.amount_paid = float(Decimal(str(bill.amount_paid)) - Decimal(str(refund_amount)))
            bill.balance_due = float(Decimal(str(bill.total_amount)) - Decimal(str(bill.amount_paid)))
            bill.status = "PARTIALLY_PAID" if bill.balance_due > 0 else "PAID"
        if already_refunded + refund_amount >= payment_amount - 0.01:
            payment.status = "REFUNDED"
        await self.db.flush()
        self._audit("PAYMENT", payment_id, "REFUND", new_value={"refund_id": str(refund.id), "amount": refund_amount})
        return refund

    async def run_ipd_daily_bed_charges(self, bill_id: UUID, from_date: date, to_date: date, bed_rate_per_day: float) -> int:
        """Add IPD charges for bed for each day in range. Returns count of charges added."""
        bill = await self.repo.get_bill(bill_id)
        if not bill or bill.bill_type != "IPD":
            raise BusinessLogicError("IPD bill not found", [BILL_NOT_FOUND])
        if not bill.admission_id:
            raise BusinessLogicError("IPD bill has no admission", ["INVALID_IPD_BILL"])
        added = 0
        d = from_date
        while d <= to_date:
            charge = IPDCharge(
                id=uuid.uuid4(),
                hospital_id=self.hospital_id,
                bill_id=bill_id,
                admission_id=bill.admission_id,
                charge_date=d,
                charge_type="BED",
                reference_id=None,
                amount=Decimal(str(bed_rate_per_day)),
            )
            self.db.add(charge)
            await self.db.flush()
            added += 1
            # next day
            from datetime import timedelta
            d = d + timedelta(days=1)
        # Recalculate bill from items + ipd_charges
        charges_r = await self.db.execute(
            select(IPDCharge).where(and_(IPDCharge.bill_id == bill_id))
        )
        charges = list(charges_r.scalars().all())
        extra = sum(float(c.amount) for c in charges)
        bill.subtotal = float(Decimal(str(bill.subtotal)) + Decimal(str(extra)))
        bill.total_amount = float(Decimal(str(bill.total_amount)) + Decimal(str(extra)))
        bill.balance_due = float(Decimal(str(bill.total_amount)) - Decimal(str(bill.amount_paid)))
        await self.db.flush()
        return added

    async def run_reconciliation(
        self,
        recon_date: date,
        total_cash: float,
        total_card: float,
        total_upi: float,
        total_online: float,
        gateway_report_total: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Reconciliation:
        """Create daily reconciliation. Compute discrepancy if gateway total provided."""
        total = total_cash + total_card + total_upi + total_online
        discrepancy = None
        status = "OK"
        if gateway_report_total is not None:
            discrepancy = total - gateway_report_total
            if abs(discrepancy) > 0.01:
                status = "DISCREPANCY"
        rec = Reconciliation(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            recon_date=recon_date,
            total_cash=Decimal(str(total_cash)),
            total_card=Decimal(str(total_card)),
            total_upi=Decimal(str(total_upi)),
            total_online=Decimal(str(total_online)),
            gateway_report_total=Decimal(str(gateway_report_total)) if gateway_report_total is not None else None,
            discrepancy_amount=Decimal(str(discrepancy)) if discrepancy is not None else None,
            status=status,
            notes=notes,
            created_by_user_id=self.user_id,
        )
        return await self.repo.create_reconciliation(rec)
