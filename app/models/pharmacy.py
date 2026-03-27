"""
Pharmacy Module Database Models
Multi-tenant pharmacy management with strict inventory control and audit logging.

CRITICAL RULES:
- All models inherit from TenantBaseModel for hospital isolation
- Stock changes MUST create StockLedger entries
- Batch tracking with FEFO (First Expiry First Out)
- Concurrency-safe stock operations with SELECT FOR UPDATE
"""
from sqlalchemy import (
    Column, String, Integer, Numeric, Date, DateTime, Boolean, 
    ForeignKey, Text, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBaseModel
from app.core.database_types import UUID_TYPE
from app.core.enums import (
    DosageForm, SupplierStatus, PurchaseOrderStatus,
    PaymentTerms
)


# ============================================================================
# MEDICINE MASTER
# ============================================================================

class Medicine(TenantBaseModel):
    """
    Medicine catalog - hospital-scoped medicine database.
    Supports search by generic/brand name, composition, manufacturer.
    """
    __tablename__ = "pharmacy_medicines"
    
    # Basic Information
    generic_name = Column(String(255), nullable=False, index=True)
    brand_name = Column(String(255), nullable=True, index=True)
    composition = Column(Text, nullable=True)  # Active ingredients
    dosage_form = Column(String(50), nullable=False)  # TABLET, SYRUP, etc.
    strength = Column(String(100), nullable=True)  # e.g., "500mg", "10mg/ml"
    manufacturer = Column(String(255), nullable=True, index=True)
    
    # Classification
    drug_class = Column(String(100), nullable=True)  # Therapeutic class
    category = Column(String(50), nullable=True)  # ANTIBIOTIC, PAINKILLER, etc.
    route = Column(String(50), nullable=True)  # ORAL, IV, TOPICAL, etc.
    
    # Inventory Control
    pack_size = Column(Integer, nullable=True)  # Units per pack
    reorder_level = Column(Integer, default=10, nullable=False)  # Min stock alert threshold
    
    # Identification
    barcode = Column(String(100), nullable=True, index=True)
    hsn_code = Column(String(20), nullable=True)  # HSN/SAC code for GST
    sku = Column(String(100), nullable=True, index=True)
    
    # Prescription Control
    requires_prescription = Column(Boolean, default=False, nullable=False)
    is_controlled_substance = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    description = Column(Text, nullable=True)
    storage_instructions = Column(Text, nullable=True)
    
    # Relationships
    stock_batches = relationship("StockBatch", back_populates="medicine", cascade="all, delete-orphan")
    ledger_entries = relationship("StockLedger", back_populates="medicine")
    hospital = relationship("Hospital", back_populates="medicines")
    
    __table_args__ = (
        Index('idx_medicine_search', 'hospital_id', 'generic_name', 'brand_name'),
        Index('idx_medicine_active', 'hospital_id', 'is_active'),
    )


# ============================================================================
# SUPPLIER MANAGEMENT
# ============================================================================

class Supplier(TenantBaseModel):
    """
    Supplier/vendor master for purchase management.
    """
    __tablename__ = "pharmacy_suppliers"
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), default="India", nullable=False)
    
    # Business Details
    gstin = Column(String(15), nullable=True)  # GST Identification Number
    drug_license_no = Column(String(100), nullable=True)
    payment_terms = Column(String(50), default=PaymentTerms.NET_30.value, nullable=False)
    credit_limit = Column(Numeric(12, 2), nullable=True)
    
    # Rating & Status
    rating = Column(Integer, nullable=True)  # 1-5 star rating
    status = Column(String(20), default=SupplierStatus.ACTIVE.value, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    grns = relationship("GoodsReceipt", back_populates="supplier")
    returns = relationship("Return", back_populates="supplier")
    hospital = relationship("Hospital", back_populates="suppliers")
    
    __table_args__ = (
        Index('idx_supplier_hospital_name', 'hospital_id', 'name'),
        Index('idx_supplier_status', 'hospital_id', 'status'),
    )


# ============================================================================
# PURCHASE ORDER MANAGEMENT
# ============================================================================

class PurchaseOrder(TenantBaseModel):
    """
    Purchase order for medicines from suppliers.
    Supports approval workflow and partial receiving.
    """
    __tablename__ = "pharmacy_purchase_orders"
    
    supplier_id = Column(UUID_TYPE, ForeignKey("pharmacy_suppliers.id"), nullable=False)
    po_number = Column(String(50), nullable=False, index=True)  # Unique per hospital
    status = Column(String(30), nullable=False, default=PurchaseOrderStatus.DRAFT.value)
    
    # Dates
    expected_date = Column(Date, nullable=True)  # Expected delivery date
    approved_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    
    # Financial summary
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax_total = Column(Numeric(12, 2), nullable=False, default=0)
    discount_total = Column(Numeric(12, 2), nullable=False, default=0)
    grand_total = Column(Numeric(12, 2), nullable=False, default=0)
    
    # Workflow
    created_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    approved_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")
    grns = relationship("GoodsReceipt", back_populates="purchase_order")
    hospital = relationship("Hospital", back_populates="purchase_orders")
    
    __table_args__ = (
        UniqueConstraint('hospital_id', 'po_number', name='uq_po_hospital_number'),
        Index('idx_po_hospital_status', 'hospital_id', 'status'),
        Index('idx_po_supplier', 'hospital_id', 'supplier_id'),
    )


class PurchaseOrderItem(TenantBaseModel):
    """
    Individual items in a purchase order.
    """
    __tablename__ = "pharmacy_purchase_order_items"
    
    po_id = Column(UUID_TYPE, ForeignKey("pharmacy_purchase_orders.id", ondelete="CASCADE"), nullable=False)
    medicine_id = Column(UUID_TYPE, ForeignKey("pharmacy_medicines.id"), nullable=False)
    
    ordered_qty = Column(Numeric(10, 3), nullable=False)
    received_qty = Column(Numeric(10, 3), nullable=False, default=0)  # Track partial receives
    purchase_rate = Column(Numeric(10, 2), nullable=False)  # Per unit price
    tax_percent = Column(Numeric(5, 2), default=0)
    discount_percent = Column(Numeric(5, 2), default=0)
    line_total = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    medicine = relationship("Medicine")
    
    __table_args__ = (
        Index('idx_po_item_po', 'po_id'),
        CheckConstraint('ordered_qty > 0', name='chk_po_item_qty_positive'),
    )


# ============================================================================
# GOODS RECEIPT NOTE (GRN)
# ============================================================================

class GoodsReceipt(TenantBaseModel):
    """
    Goods Receipt Note (GRN) - records actual receipt of medicines.
    On finalization, creates StockBatch entries and updates inventory.
    """
    __tablename__ = "pharmacy_grns"
    
    supplier_id = Column(UUID_TYPE, ForeignKey("pharmacy_suppliers.id"), nullable=False)
    po_id = Column(UUID_TYPE, ForeignKey("pharmacy_purchase_orders.id"), nullable=True)  # Optional - can receive without PO
    grn_number = Column(String(50), nullable=False, index=True)
    
    received_at = Column(DateTime, nullable=False)
    received_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    finalized_at = Column(DateTime, nullable=True)  # When GRN was finalized
    finalized_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    
    is_finalized = Column(Boolean, default=False, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="grns")
    purchase_order = relationship("PurchaseOrder", back_populates="grns")
    items = relationship("GoodsReceiptItem", back_populates="grn", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('hospital_id', 'grn_number', name='uq_grn_hospital_number'),
        Index('idx_grn_hospital_finalized', 'hospital_id', 'is_finalized'),
    )


class GoodsReceiptItem(TenantBaseModel):
    """
    Individual items received in a GRN.
    Each item creates or updates a StockBatch.
    """
    __tablename__ = "pharmacy_grn_items"
    
    grn_id = Column(UUID_TYPE, ForeignKey("pharmacy_grns.id", ondelete="CASCADE"), nullable=False)
    medicine_id = Column(UUID_TYPE, ForeignKey("pharmacy_medicines.id"), nullable=False)
    
    batch_no = Column(String(100), nullable=False)  # Batch/lot number
    expiry_date = Column(Date, nullable=False, index=True)
    received_qty = Column(Numeric(10, 3), nullable=False)
    free_qty = Column(Numeric(10, 3), default=0)  # Free samples/promotional items
    purchase_rate = Column(Numeric(10, 2), nullable=False)  # Cost price
    mrp = Column(Numeric(10, 2), nullable=False)  # Maximum Retail Price
    selling_price = Column(Numeric(10, 2), nullable=False)  # Selling price
    tax_percent = Column(Numeric(5, 2), default=0)
    
    # Relationships
    grn = relationship("GoodsReceipt", back_populates="items")
    medicine = relationship("Medicine")
    
    __table_args__ = (
        Index('idx_grn_item_grn', 'grn_id'),
        CheckConstraint('received_qty > 0', name='chk_grn_item_qty_positive'),
    )


# ============================================================================
# STOCK BATCH MANAGEMENT
# ============================================================================

class StockBatch(TenantBaseModel):
    """
    Stock batches - tracks actual inventory with batch/lot and expiry.
    This is the source of truth for available stock.
    Uses FEFO (First Expiry First Out) for sales.
    """
    __tablename__ = "pharmacy_stock_batches"
    
    medicine_id = Column(UUID_TYPE, ForeignKey("pharmacy_medicines.id"), nullable=False)
    batch_no = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    
    # Pricing
    purchase_rate = Column(Numeric(10, 2), nullable=False)
    mrp = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False)
    
    # Stock quantities
    qty_on_hand = Column(Numeric(10, 3), nullable=False, default=0)
    qty_reserved = Column(Numeric(10, 3), nullable=False, default=0)  # Reserved for pending sales
    
    # Reorder level (optional - can be at medicine level)
    reorder_level = Column(Numeric(10, 3), nullable=True)
    
    # Source tracking
    grn_item_id = Column(UUID_TYPE, ForeignKey("pharmacy_grn_items.id"), nullable=True)  # Which GRN created this batch
    
    # Unique constraint: same batch_no + expiry_date per medicine per hospital
    __table_args__ = (
        UniqueConstraint('hospital_id', 'medicine_id', 'batch_no', 'expiry_date', name='uq_stock_batch'),
        Index('idx_stock_batch_medicine', 'hospital_id', 'medicine_id'),
        Index('idx_stock_batch_expiry', 'hospital_id', 'expiry_date'),
        Index('idx_stock_batch_available', 'hospital_id', 'medicine_id', 'expiry_date', 'qty_on_hand'),
        CheckConstraint('qty_on_hand >= 0', name='chk_stock_batch_qty_non_negative'),
        CheckConstraint('qty_reserved >= 0', name='chk_stock_batch_reserved_non_negative'),
    )
    
    # Relationships
    medicine = relationship("Medicine", back_populates="stock_batches")
    ledger_entries = relationship("StockLedger", back_populates="batch")
    sale_items = relationship("SaleItem", back_populates="batch")
    hospital = relationship("Hospital", back_populates="stock_batches")


# ============================================================================
# STOCK LEDGER (AUDIT TRAIL)
# ============================================================================

class StockLedger(TenantBaseModel):
    """
    Append-only stock ledger for complete audit trail.
    Every stock-affecting operation creates a ledger entry.
    """
    __tablename__ = "pharmacy_stock_ledger"
    
    medicine_id = Column(UUID_TYPE, ForeignKey("pharmacy_medicines.id"), nullable=False, index=True)
    batch_id = Column(UUID_TYPE, ForeignKey("pharmacy_stock_batches.id"), nullable=True)  # Nullable for adjustments without batch
    
    # Transaction details
    txn_type = Column(String(30), nullable=False, index=True)  # GRN_IN, SALE_OUT, RETURN_IN, RETURN_TO_SUPPLIER_OUT, ADJUSTMENT, TRANSFER
    qty_change = Column(Numeric(10, 3), nullable=False)  # Positive for IN, negative for OUT
    unit_cost = Column(Numeric(10, 2), nullable=False)  # Cost at time of transaction
    
    # Reference tracking
    reference_type = Column(String(50), nullable=True)  # GRN, SALE, RETURN, ADJUSTMENT, etc.
    reference_id = Column(UUID_TYPE, nullable=True)  # ID of the related record
    
    # Audit
    performed_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=True)  # Reason for adjustment/transfer
    
    __table_args__ = (
        Index('idx_ledger_medicine_date', 'hospital_id', 'medicine_id', 'created_at'),
        Index('idx_ledger_txn_type', 'hospital_id', 'txn_type', 'created_at'),
    )
    
    # Relationships
    medicine = relationship("Medicine", back_populates="ledger_entries")
    batch = relationship("StockBatch", back_populates="ledger_entries")


# ============================================================================
# SALES / DISPENSING
# ============================================================================

class Sale(TenantBaseModel):
    """
    Pharmacy sales - prescription-based or OTC (Over The Counter).
    On completion, deducts stock from batches using FEFO.
    """
    __tablename__ = "pharmacy_sales"
    
    sale_number = Column(String(50), nullable=False, index=True)  # Unique per hospital
    sale_type = Column(String(20), nullable=False)  # PRESCRIPTION or OTC
    status = Column(String(20), nullable=False, default="DRAFT")
    
    # Patient/Doctor context (nullable for OTC)
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=True)
    doctor_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)  # Prescribing doctor
    prescription_id = Column(UUID_TYPE, nullable=True)  # Reference to prescription (if exists)
    
    # Billing context
    billed_via = Column(String(20), nullable=False)  # PHARMACY_COUNTER, OPD, IPD
    billing_invoice_id = Column(UUID_TYPE, nullable=True)  # Link to billing invoice if integrated
    
    # Financial totals
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax_total = Column(Numeric(12, 2), nullable=False, default=0)
    discount_total = Column(Numeric(12, 2), nullable=False, default=0)
    grand_total = Column(Numeric(12, 2), nullable=False, default=0)
    
    # Payment
    payment_status = Column(String(20), nullable=False, default="PENDING")
    payment_method = Column(String(20), nullable=True)  # CASH, CARD, UPI, CREDIT
    paid_amount = Column(Numeric(12, 2), default=0)
    
    # Workflow
    created_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    voided_at = Column(DateTime, nullable=True)
    voided_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    void_reason = Column(Text, nullable=True)
    
    # Idempotency
    idempotency_key = Column(String(100), unique=True, index=True)  # Prevent duplicate sales
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    hospital = relationship("Hospital", back_populates="sales")
    patient = relationship("PatientProfile", back_populates="sales")
    
    __table_args__ = (
        UniqueConstraint('hospital_id', 'sale_number', name='uq_sale_hospital_number'),
        Index('idx_sale_patient', 'hospital_id', 'patient_id', 'created_at'),
        Index('idx_sale_date', 'hospital_id', 'created_at'),
    )


class SaleItem(TenantBaseModel):
    """
    Individual items in a sale.
    Links to specific batch for FEFO tracking.
    """
    __tablename__ = "pharmacy_sale_items"
    
    sale_id = Column(UUID_TYPE, ForeignKey("pharmacy_sales.id", ondelete="CASCADE"), nullable=False)
    medicine_id = Column(UUID_TYPE, ForeignKey("pharmacy_medicines.id"), nullable=False)
    batch_id = Column(UUID_TYPE, ForeignKey("pharmacy_stock_batches.id"), nullable=False)
    
    qty = Column(Numeric(10, 3), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), default=0)
    tax = Column(Numeric(10, 2), default=0)
    line_total = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    sale = relationship("Sale", back_populates="items")
    medicine = relationship("Medicine")
    batch = relationship("StockBatch", back_populates="sale_items")
    
    __table_args__ = (
        Index('idx_sale_item_sale', 'sale_id'),
        CheckConstraint('qty > 0', name='chk_sale_item_qty_positive'),
    )


# ============================================================================
# RETURNS
# ============================================================================

class Return(TenantBaseModel):
    """
    Patient returns or supplier returns.
    """
    __tablename__ = "pharmacy_returns"
    
    return_number = Column(String(50), nullable=False, index=True)
    return_type = Column(String(30), nullable=False)  # PATIENT_RETURN or SUPPLIER_RETURN
    
    # Source sale (for patient returns)
    sale_id = Column(UUID_TYPE, ForeignKey("pharmacy_sales.id"), nullable=True)
    
    # Supplier (for supplier returns)
    supplier_id = Column(UUID_TYPE, ForeignKey("pharmacy_suppliers.id"), nullable=True)
    grn_id = Column(UUID_TYPE, ForeignKey("pharmacy_grns.id"), nullable=True)  # Original GRN for supplier returns
    
    # Patient (for patient returns)
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=True)
    
    # Totals
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    
    # Workflow
    returned_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    return_reason = Column(Text, nullable=True)
    returned_at = Column(DateTime, nullable=False)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="returns")
    sale = relationship("Sale", foreign_keys=[sale_id])
    grn = relationship("GoodsReceipt", foreign_keys=[grn_id])
    patient = relationship("PatientProfile", foreign_keys=[patient_id])
    items = relationship("ReturnItem", back_populates="return_record", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('hospital_id', 'return_number', name='uq_return_hospital_number'),
    )


class ReturnItem(TenantBaseModel):
    """
    Individual items in a return.
    """
    __tablename__ = "pharmacy_return_items"
    
    return_id = Column(UUID_TYPE, ForeignKey("pharmacy_returns.id", ondelete="CASCADE"), nullable=False)
    medicine_id = Column(UUID_TYPE, ForeignKey("pharmacy_medicines.id"), nullable=False)
    batch_id = Column(UUID_TYPE, ForeignKey("pharmacy_stock_batches.id"), nullable=True)  # Nullable - may create new batch for returns
    
    qty = Column(Numeric(10, 3), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    return_record = relationship("Return", back_populates="items")
    medicine = relationship("Medicine")
    batch = relationship("StockBatch")
    
    __table_args__ = (
        Index('idx_return_item_return', 'return_id'),
        CheckConstraint('qty > 0', name='chk_return_item_qty_positive'),
    )


# ============================================================================
# EXPIRY ALERTS
# ============================================================================

class ExpiryAlert(TenantBaseModel):
    """
    Expiry alerts for batches nearing expiration.
    Created by background job, can be acknowledged.
    """
    __tablename__ = "pharmacy_expiry_alerts"
    
    batch_id = Column(UUID_TYPE, ForeignKey("pharmacy_stock_batches.id"), nullable=False)
    alert_type = Column(String(30), nullable=False)  # NEAR_EXPIRY, EXPIRED, LOW_STOCK
    threshold_days = Column(Integer, nullable=True)  # Days until expiry (for NEAR_EXPIRY)
    
    status = Column(String(20), nullable=False, default="OPEN")  # OPEN, ACKNOWLEDGED, CLOSED
    acknowledged_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Relationships
    batch = relationship("StockBatch")
    
    __table_args__ = (
        Index('idx_alert_batch_status', 'hospital_id', 'batch_id', 'status'),
        Index('idx_alert_type_status', 'hospital_id', 'alert_type', 'status'),
    )
