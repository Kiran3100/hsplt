"""create_pharmacy_tables

Revision ID: pharmacy_001
Revises: 
Create Date: 2026-02-19

Complete pharmacy module tables with strict tenant isolation and inventory control.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = 'pharmacy_001'
down_revision = 'd38c70f097c0'  # Branch from initial (efd55c6d7099 was missing)
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    return name in inspect(conn).get_table_names()


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, 'pharmacy_medicines'):
        op.create_table(
        'pharmacy_medicines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('generic_name', sa.String(255), nullable=False, index=True),
        sa.Column('brand_name', sa.String(255), nullable=True, index=True),
        sa.Column('composition', sa.Text, nullable=True),
        sa.Column('dosage_form', sa.String(50), nullable=False),
        sa.Column('strength', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(255), nullable=True, index=True),
        sa.Column('drug_class', sa.String(100), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('route', sa.String(50), nullable=True),
        sa.Column('pack_size', sa.Integer, nullable=True),
        sa.Column('reorder_level', sa.Integer, nullable=False, default=10),
        sa.Column('barcode', sa.String(100), nullable=True, index=True),
        sa.Column('hsn_code', sa.String(20), nullable=True),
        sa.Column('sku', sa.String(100), nullable=True, index=True),
        sa.Column('requires_prescription', sa.Boolean, nullable=False, default=False),
        sa.Column('is_controlled_substance', sa.Boolean, nullable=False, default=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('storage_instructions', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
        op.create_index('idx_medicine_search', 'pharmacy_medicines', ['hospital_id', 'generic_name', 'brand_name'])
        op.create_index('idx_medicine_active', 'pharmacy_medicines', ['hospital_id', 'is_active'])

    if not _table_exists(conn, 'pharmacy_suppliers'):
        op.create_table(
        'pharmacy_suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address_line1', sa.String(255), nullable=True),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('pincode', sa.String(10), nullable=True),
        sa.Column('country', sa.String(100), nullable=False, default='India'),
        sa.Column('gstin', sa.String(15), nullable=True),
        sa.Column('drug_license_no', sa.String(100), nullable=True),
        sa.Column('payment_terms', sa.String(50), nullable=False, default='NET_30'),
        sa.Column('credit_limit', sa.Numeric(12, 2), nullable=True),
        sa.Column('rating', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='ACTIVE'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
        op.create_index('idx_supplier_hospital_name', 'pharmacy_suppliers', ['hospital_id', 'name'])
        op.create_index('idx_supplier_status', 'pharmacy_suppliers', ['hospital_id', 'status'])

    if not _table_exists(conn, 'pharmacy_purchase_orders'):
        op.create_table(
        'pharmacy_purchase_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_suppliers.id'), nullable=False),
        sa.Column('po_number', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(30), nullable=False, default='DRAFT'),
        sa.Column('expected_date', sa.Date, nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('sent_at', sa.DateTime, nullable=True),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('tax_total', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('discount_total', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('grand_total', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('hospital_id', 'po_number', name='uq_po_hospital_number'),
    )
        op.create_index('idx_po_hospital_status', 'pharmacy_purchase_orders', ['hospital_id', 'status'])
        op.create_index('idx_po_supplier', 'pharmacy_purchase_orders', ['hospital_id', 'supplier_id'])

    if not _table_exists(conn, 'pharmacy_purchase_order_items'):
        op.create_table(
        'pharmacy_purchase_order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_purchase_orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_medicines.id'), nullable=False),
        sa.Column('ordered_qty', sa.Numeric(10, 3), nullable=False),
        sa.Column('received_qty', sa.Numeric(10, 3), nullable=False, default=0),
        sa.Column('purchase_rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_percent', sa.Numeric(5, 2), default=0),
        sa.Column('discount_percent', sa.Numeric(5, 2), default=0),
        sa.Column('line_total', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint('ordered_qty > 0', name='chk_po_item_qty_positive'),
    )
        op.create_index('idx_po_item_po', 'pharmacy_purchase_order_items', ['po_id'])

    if not _table_exists(conn, 'pharmacy_grns'):
        op.create_table(
        'pharmacy_grns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_suppliers.id'), nullable=False),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_purchase_orders.id'), nullable=True),
        sa.Column('grn_number', sa.String(50), nullable=False, index=True),
        sa.Column('received_at', sa.DateTime, nullable=False),
        sa.Column('received_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('finalized_at', sa.DateTime, nullable=True),
        sa.Column('finalized_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_finalized', sa.Boolean, nullable=False, default=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('hospital_id', 'grn_number', name='uq_grn_hospital_number'),
    )
        op.create_index('idx_grn_hospital_finalized', 'pharmacy_grns', ['hospital_id', 'is_finalized'])

    if not _table_exists(conn, 'pharmacy_grn_items'):
        op.create_table(
        'pharmacy_grn_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('grn_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_grns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_medicines.id'), nullable=False),
        sa.Column('batch_no', sa.String(100), nullable=False),
        sa.Column('expiry_date', sa.Date, nullable=False, index=True),
        sa.Column('received_qty', sa.Numeric(10, 3), nullable=False),
        sa.Column('free_qty', sa.Numeric(10, 3), default=0),
        sa.Column('purchase_rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('mrp', sa.Numeric(10, 2), nullable=False),
        sa.Column('selling_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_percent', sa.Numeric(5, 2), default=0),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint('received_qty > 0', name='chk_grn_item_qty_positive'),
    )
        op.create_index('idx_grn_item_grn', 'pharmacy_grn_items', ['grn_id'])

    if not _table_exists(conn, 'pharmacy_stock_batches'):
        op.create_table(
        'pharmacy_stock_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_medicines.id'), nullable=False),
        sa.Column('batch_no', sa.String(100), nullable=False),
        sa.Column('expiry_date', sa.Date, nullable=False, index=True),
        sa.Column('purchase_rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('mrp', sa.Numeric(10, 2), nullable=False),
        sa.Column('selling_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('qty_on_hand', sa.Numeric(10, 3), nullable=False, default=0),
        sa.Column('qty_reserved', sa.Numeric(10, 3), nullable=False, default=0),
        sa.Column('reorder_level', sa.Numeric(10, 3), nullable=True),
        sa.Column('grn_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_grn_items.id'), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('hospital_id', 'medicine_id', 'batch_no', 'expiry_date', name='uq_stock_batch'),
        sa.CheckConstraint('qty_on_hand >= 0', name='chk_stock_batch_qty_non_negative'),
        sa.CheckConstraint('qty_reserved >= 0', name='chk_stock_batch_reserved_non_negative'),
    )
        op.create_index('idx_stock_batch_medicine', 'pharmacy_stock_batches', ['hospital_id', 'medicine_id'])
        op.create_index('idx_stock_batch_expiry', 'pharmacy_stock_batches', ['hospital_id', 'expiry_date'])
        op.create_index('idx_stock_batch_available', 'pharmacy_stock_batches', ['hospital_id', 'medicine_id', 'expiry_date', 'qty_on_hand'])

    if not _table_exists(conn, 'pharmacy_stock_ledger'):
        op.create_table(
        'pharmacy_stock_ledger',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_medicines.id'), nullable=False, index=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_stock_batches.id'), nullable=True),
        sa.Column('txn_type', sa.String(30), nullable=False, index=True),
        sa.Column('qty_change', sa.Numeric(10, 3), nullable=False),
        sa.Column('unit_cost', sa.Numeric(10, 2), nullable=False),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('performed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
        op.create_index('idx_ledger_medicine_date', 'pharmacy_stock_ledger', ['hospital_id', 'medicine_id', 'created_at'])
        op.create_index('idx_ledger_txn_type', 'pharmacy_stock_ledger', ['hospital_id', 'txn_type', 'created_at'])

    if not _table_exists(conn, 'pharmacy_sales'):
        op.create_table(
        'pharmacy_sales',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('sale_number', sa.String(50), nullable=False, index=True),
        sa.Column('sale_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='DRAFT'),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patient_profiles.id'), nullable=True),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('prescription_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('billed_via', sa.String(20), nullable=False),
        sa.Column('billing_invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('tax_total', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('discount_total', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('grand_total', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('payment_status', sa.String(20), nullable=False, default='PENDING'),
        sa.Column('payment_method', sa.String(20), nullable=True),
        sa.Column('paid_amount', sa.Numeric(12, 2), default=0),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('voided_at', sa.DateTime, nullable=True),
        sa.Column('voided_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('void_reason', sa.Text, nullable=True),
        sa.Column('idempotency_key', sa.String(100), unique=True, index=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('hospital_id', 'sale_number', name='uq_sale_hospital_number'),
    )
        op.create_index('idx_sale_patient', 'pharmacy_sales', ['hospital_id', 'patient_id', 'created_at'])
        op.create_index('idx_sale_date', 'pharmacy_sales', ['hospital_id', 'created_at'])

    if not _table_exists(conn, 'pharmacy_sale_items'):
        op.create_table(
        'pharmacy_sale_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('sale_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_sales.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_medicines.id'), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_stock_batches.id'), nullable=False),
        sa.Column('qty', sa.Numeric(10, 3), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('discount', sa.Numeric(10, 2), default=0),
        sa.Column('tax', sa.Numeric(10, 2), default=0),
        sa.Column('line_total', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint('qty > 0', name='chk_sale_item_qty_positive'),
    )
        op.create_index('idx_sale_item_sale', 'pharmacy_sale_items', ['sale_id'])

    if not _table_exists(conn, 'pharmacy_returns'):
        op.create_table(
        'pharmacy_returns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('return_number', sa.String(50), nullable=False, index=True),
        sa.Column('return_type', sa.String(30), nullable=False),
        sa.Column('sale_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_sales.id'), nullable=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_suppliers.id'), nullable=True),
        sa.Column('grn_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_grns.id'), nullable=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patient_profiles.id'), nullable=True),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False, default=0),
        sa.Column('returned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('return_reason', sa.Text, nullable=True),
        sa.Column('returned_at', sa.DateTime, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('hospital_id', 'return_number', name='uq_return_hospital_number'),
    )

    if not _table_exists(conn, 'pharmacy_return_items'):
        op.create_table(
        'pharmacy_return_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('return_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_returns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_medicines.id'), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_stock_batches.id'), nullable=True),
        sa.Column('qty', sa.Numeric(10, 3), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('line_total', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint('qty > 0', name='chk_return_item_qty_positive'),
    )
        op.create_index('idx_return_item_return', 'pharmacy_return_items', ['return_id'])

    if not _table_exists(conn, 'pharmacy_expiry_alerts'):
        op.create_table(
        'pharmacy_expiry_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False, index=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pharmacy_stock_batches.id'), nullable=False),
        sa.Column('alert_type', sa.String(30), nullable=False),
        sa.Column('threshold_days', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='OPEN'),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
        op.create_index('idx_alert_batch_status', 'pharmacy_expiry_alerts', ['hospital_id', 'batch_id', 'status'])
        op.create_index('idx_alert_type_status', 'pharmacy_expiry_alerts', ['hospital_id', 'alert_type', 'status'])


def downgrade():
    op.drop_table('pharmacy_expiry_alerts')
    op.drop_table('pharmacy_return_items')
    op.drop_table('pharmacy_returns')
    op.drop_table('pharmacy_sale_items')
    op.drop_table('pharmacy_sales')
    op.drop_table('pharmacy_stock_ledger')
    op.drop_table('pharmacy_stock_batches')
    op.drop_table('pharmacy_grn_items')
    op.drop_table('pharmacy_grns')
    op.drop_table('pharmacy_purchase_order_items')
    op.drop_table('pharmacy_purchase_orders')
    op.drop_table('pharmacy_suppliers')
    op.drop_table('pharmacy_medicines')
