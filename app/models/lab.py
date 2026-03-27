"""
Lab Test Registration Models
Handles lab test catalogue, orders, order items, and sample collection for hospital lab operations.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Text, Boolean, Integer, DECIMAL, DateTime, ForeignKey, UniqueConstraint
from app.core.database_types import UUID_TYPE, JSON_TYPE
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import BaseModel
from app.core.enums import (
    SampleType, LabOrderSource, LabOrderPriority, LabOrderStatus,
    LabTestStatus, LabOrderItemStatus, SampleStatus, ContainerType, RejectionReason,
    ResultStatus, ResultFlag
)


class LabTestCategory(BaseModel):
    """
    Lab Test Category / Department - Groups tests by department (e.g. Hematology, Biochemistry).
    """
    __tablename__ = "lab_test_categories"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)

    category_code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    hospital = relationship("Hospital", back_populates="lab_test_categories")
    tests = relationship("LabTest", back_populates="category")

    __table_args__ = (
        # Unique category code per hospital
        {"schema": None}
    )

    def __repr__(self):
        return f"<LabTestCategory(code='{self.category_code}', name='{self.name}')>"


class LabTest(BaseModel):
    """
    Lab Test Catalogue - Master data for available lab tests
    """
    __tablename__ = "lab_tests"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    category_id = Column(UUID_TYPE, ForeignKey("lab_test_categories.id"), nullable=True, index=True)

    # Test identification
    test_code = Column(String(50), nullable=False, index=True)  # e.g., "CBC", "TSH"
    test_name = Column(String(255), nullable=False)  # e.g., "Complete Blood Count"

    # Test specifications
    sample_type = Column(String(20), nullable=False)  # SampleType enum (specimen type)
    turnaround_time_hours = Column(Integer, nullable=False, default=24)
    price = Column(DECIMAL(10, 2), nullable=True)  # Pricing field; no billing integration
    unit = Column(String(50), nullable=True)  # Result unit e.g. g/dL, mg/L
    methodology = Column(String(255), nullable=True)  # e.g. "Automated", "Manual", "ELISA"

    # Test details
    description = Column(Text, nullable=True)
    preparation_instructions = Column(Text, nullable=True)
    reference_ranges = Column(JSON_TYPE, nullable=True, default=lambda: {})  # Normal ranges (optionally by gender/age)

    # Status and metadata
    status = Column(String(20), nullable=False, default=LabTestStatus.ACTIVE)
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    hospital = relationship("Hospital", back_populates="lab_tests")
    category = relationship("LabTestCategory", back_populates="tests")
    order_items = relationship("LabOrderItem", back_populates="test")
    equipment_mappings = relationship("EquipmentTestMap", back_populates="test", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        # Unique test code per hospital
        {"schema": None}
    )
    
    def __repr__(self):
        return f"<LabTest(code='{self.test_code}', name='{self.test_name}')>"


class LabOrder(BaseModel):
    """
    Lab Order - Container for one or more lab tests for a patient
    """
    __tablename__ = "lab_orders"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # Order identification (unique per hospital)
    lab_order_no = Column(String(50), nullable=False, index=True)  # e.g., "LAB-2026-00045"
    
    # Patient and doctor references
    patient_id = Column(String(50), nullable=False, index=True)  # Patient reference (PAT-XXXXX)
    requested_by_doctor_id = Column(String(50), nullable=True, index=True)  # Doctor reference (DOC-XXXXX)
    
    # Order details
    source = Column(String(20), nullable=False)  # LabOrderSource enum
    priority = Column(String(20), nullable=False, default=LabOrderPriority.ROUTINE)
    status = Column(String(20), nullable=False, default=LabOrderStatus.REGISTERED)
    
    # Additional references (optional)
    encounter_id = Column(String(50), nullable=True)  # Link to OPD/IPD encounter
    prescription_id = Column(String(50), nullable=True)  # Link to prescription
    
    # Order metadata
    notes = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    sample_collection_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Cancellation details
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(String(100), nullable=True)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="lab_orders")
    order_items = relationship("LabOrderItem", back_populates="order", cascade="all, delete-orphan")
    samples = relationship("Sample", back_populates="order", cascade="all, delete-orphan")
    lab_reports = relationship("LabReport", back_populates="lab_order")
    share_tokens = relationship("ReportShareToken", back_populates="lab_order")
    access_logs = relationship("ReportAccess", back_populates="lab_order")

    __table_args__ = (UniqueConstraint("hospital_id", "lab_order_no", name="uq_lab_order_no_per_hospital"),)

    def __repr__(self):
        return f"<LabOrder(no='{self.lab_order_no}', patient='{self.patient_id}')>"


class LabOrderItem(BaseModel):
    """
    Lab Order Item - Individual test within a lab order
    """
    __tablename__ = "lab_order_items"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    
    # References
    lab_order_id = Column(UUID_TYPE, ForeignKey("lab_orders.id"), nullable=False, index=True)
    test_id = Column(UUID_TYPE, ForeignKey("lab_tests.id"), nullable=False, index=True)
    
    # Item status
    status = Column(String(20), nullable=False, default=LabOrderItemStatus.REGISTERED)
    
    # Test execution details
    sample_collected_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results (for future phases)
    result_values = Column(JSON_TYPE, nullable=True, default=lambda: {})  # Store test results
    result_notes = Column(Text, nullable=True)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    order = relationship("LabOrder", back_populates="order_items")
    test = relationship("LabTest", back_populates="order_items")
    sample_items = relationship("SampleOrderItem", back_populates="order_item")
    # Multiple result versions per item (current = latest by created_at); corrections link via previous_result_id
    test_results = relationship(
        "TestResult", back_populates="order_item", uselist=True,
        order_by="TestResult.created_at.desc()"
    )
    
    def __repr__(self):
        return f"<LabOrderItem(order='{self.lab_order_id}', test='{self.test_id}')>"


class Sample(BaseModel):
    """
    Lab Sample - Physical sample collected for testing
    One sample can be used for multiple tests if same sample type
    """
    __tablename__ = "lab_samples"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # Sample identification (unique per hospital)
    sample_no = Column(String(50), nullable=False, index=True)  # e.g., "SMP-2026-00023"
    barcode_value = Column(String(100), nullable=False, index=True)  # Barcode; unique per hospital
    qr_value = Column(String(100), nullable=True, index=True)  # Optional QR code
    
    # Sample details
    lab_order_id = Column(UUID_TYPE, ForeignKey("lab_orders.id"), nullable=False, index=True)
    patient_id = Column(String(50), nullable=False, index=True)  # Patient reference
    sample_type = Column(String(20), nullable=False)  # SampleType enum
    container_type = Column(String(20), nullable=False, default=ContainerType.PLAIN)
    
    # Sample status and workflow
    status = Column(String(20), nullable=False, default=SampleStatus.REGISTERED)
    
    # Collection details
    collected_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)
    collection_site = Column(String(20), nullable=True)  # CollectionSite enum
    collector_notes = Column(Text, nullable=True)
    
    # Lab processing details
    received_in_lab_at = Column(DateTime(timezone=True), nullable=True)
    received_location = Column(String(100), nullable=True)  # Lab section/department
    received_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    
    # Rejection details
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(String(30), nullable=True)  # RejectionReason enum
    rejection_notes = Column(Text, nullable=True)
    
    # Sample metadata
    volume_ml = Column(DECIMAL(5, 2), nullable=True)  # Sample volume in ml
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="lab_samples")
    order = relationship("LabOrder", back_populates="samples")
    collector = relationship("User", foreign_keys=[collected_by])
    receiver = relationship("User", foreign_keys=[received_by])
    rejector = relationship("User", foreign_keys=[rejected_by])
    sample_items = relationship("SampleOrderItem", back_populates="sample", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="sample")
    custody_chain = relationship("ChainOfCustody", back_populates="sample", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("hospital_id", "sample_no", name="uq_sample_no_per_hospital"),
        UniqueConstraint("hospital_id", "barcode_value", name="uq_barcode_value_per_hospital"),
    )

    def __repr__(self):
        return f"<Sample(no='{self.sample_no}', type='{self.sample_type}', status='{self.status}')>"


class SampleOrderItem(BaseModel):
    """
    Bridge table linking samples to order items
    One sample can be used for multiple tests (same sample type)
    """
    __tablename__ = "sample_order_items"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    
    # References
    sample_id = Column(UUID_TYPE, ForeignKey("lab_samples.id"), nullable=False, index=True)
    lab_order_item_id = Column(UUID_TYPE, ForeignKey("lab_order_items.id"), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    sample = relationship("Sample", back_populates="sample_items")
    order_item = relationship("LabOrderItem", back_populates="sample_items")
    
    # Unique constraint to prevent duplicate mappings
    __table_args__ = (
        {"schema": None}
    )
    
    def __repr__(self):
        return f"<SampleOrderItem(sample='{self.sample_id}', item='{self.lab_order_item_id}')>"


class TestResult(BaseModel):
    """
    Lab Test Result - Stores test results for order items
    """
    __tablename__ = "test_results"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # References
    lab_order_item_id = Column(UUID_TYPE, ForeignKey("lab_order_items.id"), nullable=False, index=True)
    sample_id = Column(UUID_TYPE, ForeignKey("lab_samples.id"), nullable=False, index=True)
    
    # Result status and workflow
    status = Column(String(20), nullable=False, default=ResultStatus.DRAFT)
    
    # Entry details
    entered_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    entered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Verification details
    verified_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Release details
    released_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    release_notes = Column(Text, nullable=True)
    
    # Rejection details (if sent back for correction)
    rejected_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Pathologist approval (immutable after approval; corrections create new version)
    approved_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    signature_placeholder = Column(Text, nullable=True)  # Digital signature placeholder
    
    # Versioning: correction creates new row linked to previous approved result
    previous_result_id = Column(UUID_TYPE, ForeignKey("test_results.id"), nullable=True, index=True)
    
    # General notes and metadata
    remarks = Column(Text, nullable=True)
    technical_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="test_results")
    order_item = relationship("LabOrderItem", back_populates="test_results")
    sample = relationship("Sample", back_populates="test_results")
    entered_by_user = relationship("User", foreign_keys=[entered_by])
    verified_by_user = relationship("User", foreign_keys=[verified_by])
    released_by_user = relationship("User", foreign_keys=[released_by])
    rejected_by_user = relationship("User", foreign_keys=[rejected_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    previous_result = relationship("TestResult", remote_side="TestResult.id", backref="correction_results")
    result_values = relationship("ResultValue", back_populates="test_result", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TestResult(item='{self.lab_order_item_id}', status='{self.status}')>"


class ResultValue(BaseModel):
    """
    Individual parameter values within a test result
    For tests with multiple parameters (e.g., CBC has HB, WBC, Platelets)
    """
    __tablename__ = "result_values"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    
    # References
    test_result_id = Column(UUID_TYPE, ForeignKey("test_results.id"), nullable=False, index=True)
    
    # Parameter details
    parameter_name = Column(String(100), nullable=False)  # e.g., "HB", "WBC", "Platelets"
    value = Column(String(100), nullable=False)  # The actual result value
    unit = Column(String(50), nullable=True)  # e.g., "g/dL", "cells/uL"
    reference_range = Column(String(100), nullable=True)  # e.g., "12-16", "4000-11000"
    
    # Result interpretation
    flag = Column(String(20), nullable=True)  # ResultFlag enum: NORMAL, HIGH, LOW, etc.
    is_abnormal = Column(Boolean, nullable=False, default=False)
    
    # Parameter metadata
    display_order = Column(Integer, nullable=False, default=1)  # Order to display parameters
    notes = Column(Text, nullable=True)  # Parameter-specific notes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    test_result = relationship("TestResult", back_populates="result_values")
    
    def __repr__(self):
        return f"<ResultValue(parameter='{self.parameter_name}', value='{self.value}')>"


class LabReport(BaseModel):
    """
    Lab Report - Generated PDF reports for lab orders
    """
    __tablename__ = "lab_reports"
    __table_args__ = (UniqueConstraint("hospital_id", "report_number", name="uq_report_number_per_hospital"),)

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # References
    lab_order_id = Column(UUID_TYPE, ForeignKey("lab_orders.id"), nullable=False, index=True)
    
    # Report details (report_number unique per hospital)
    report_number = Column(String(50), nullable=False, index=True)  # e.g., "RPT-2026-00001"
    report_version = Column(Integer, nullable=False, default=1)  # Version number for regenerated reports
    
    # Report content
    pdf_path = Column(String(500), nullable=True)  # File system path to PDF
    pdf_blob_ref = Column(String(500), nullable=True)  # Cloud storage reference
    report_data = Column(JSON_TYPE, nullable=True, default=lambda: {})  # Structured report data for regeneration
    
    # Generation details
    generated_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Report metadata
    total_tests = Column(Integer, nullable=False, default=0)
    completed_tests = Column(Integer, nullable=False, default=0)
    is_final = Column(Boolean, nullable=False, default=True)  # False for partial reports
    
    # Report status
    is_active = Column(Boolean, nullable=False, default=True)  # Latest version is active
    
    # Publishing status
    publish_status = Column(String(20), nullable=False, default="DRAFT")  # ReportPublishStatus enum
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    unpublished_at = Column(DateTime(timezone=True), nullable=True)
    unpublished_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="lab_reports")
    lab_order = relationship("LabOrder", back_populates="lab_reports")
    generated_by_user = relationship("User", foreign_keys=[generated_by])
    published_by_user = relationship("User", foreign_keys=[published_by])
    unpublished_by_user = relationship("User", foreign_keys=[unpublished_by])
    share_tokens = relationship("ReportShareToken", back_populates="lab_report")
    access_logs = relationship("ReportAccess", back_populates="lab_report")
    
    def __repr__(self):
        return f"<LabReport(number='{self.report_number}', version={self.report_version})>"


# ============================================================================
# EQUIPMENT & QC MANAGEMENT MODELS
# ============================================================================

class Equipment(BaseModel):
    """
    Lab Equipment - Analyzers and instruments used in lab operations
    """
    __tablename__ = "lab_equipment"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # Equipment identification (equipment_code unique per hospital)
    equipment_code = Column(String(50), nullable=False, index=True)  # e.g., "EQ-HEMA-01"
    name = Column(String(255), nullable=False)  # e.g., "Sysmex XN-1000"
    
    # Equipment specifications
    category = Column(String(20), nullable=False)  # EquipmentCategory enum
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    
    # Status and maintenance
    status = Column(String(20), nullable=False, default="ACTIVE")  # EquipmentStatus enum
    installation_date = Column(DateTime(timezone=True), nullable=True)
    last_calibrated_at = Column(DateTime(timezone=True), nullable=True)
    next_calibration_due_at = Column(DateTime(timezone=True), nullable=True)
    
    # Equipment details
    location = Column(String(100), nullable=True)  # Lab section/room
    notes = Column(Text, nullable=True)
    specifications = Column(JSON_TYPE, nullable=True, default=lambda: {})  # Technical specifications
    
    # Status tracking
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="lab_equipment")
    maintenance_logs = relationship("EquipmentMaintenanceLog", back_populates="equipment", cascade="all, delete-orphan")
    qc_runs = relationship("QCRun", back_populates="equipment")
    test_mappings = relationship("EquipmentTestMap", back_populates="equipment", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("hospital_id", "equipment_code", name="uq_equipment_code_per_hospital"),
    )
    
    def __repr__(self):
        return f"<Equipment(code='{self.equipment_code}', name='{self.name}')>"


class EquipmentTestMap(BaseModel):
    """
    Equipment–Test mapping - Links equipment to tests they can perform.
    """
    __tablename__ = "lab_equipment_test_map"
    __table_args__ = (
        UniqueConstraint("equipment_id", "test_id", name="uq_equipment_test_per_map"),
    )

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    equipment_id = Column(UUID_TYPE, ForeignKey("lab_equipment.id"), nullable=False, index=True)
    test_id = Column(UUID_TYPE, ForeignKey("lab_tests.id"), nullable=False, index=True)
    is_primary = Column(Boolean, nullable=False, default=False)  # Primary equipment for this test
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    equipment = relationship("Equipment", back_populates="test_mappings")
    test = relationship("LabTest", back_populates="equipment_mappings")


class EquipmentMaintenanceLog(BaseModel):
    """
    Equipment Maintenance Log - Tracks calibration, maintenance, and repairs
    """
    __tablename__ = "equipment_maintenance_logs"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    
    # References
    equipment_id = Column(UUID_TYPE, ForeignKey("lab_equipment.id"), nullable=False, index=True)
    
    # Maintenance details
    type = Column(String(20), nullable=False)  # MaintenanceType enum
    performed_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    performed_at = Column(DateTime(timezone=True), nullable=False)
    
    # Scheduling
    next_due_at = Column(DateTime(timezone=True), nullable=True)
    
    # Documentation
    remarks = Column(Text, nullable=True)
    attachment_ref = Column(String(500), nullable=True)  # File reference
    cost = Column(DECIMAL(10, 2), nullable=True)
    
    # Service details
    service_provider = Column(String(200), nullable=True)  # External service provider
    service_ticket_no = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    equipment = relationship("Equipment", back_populates="maintenance_logs")
    performed_by_user = relationship("User", foreign_keys=[performed_by])
    
    def __repr__(self):
        return f"<MaintenanceLog(equipment='{self.equipment_id}', type='{self.type}')>"


class QCRule(BaseModel):
    """
    Quality Control Rules - Defines QC requirements for lab sections/tests
    """
    __tablename__ = "qc_rules"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # Rule identification
    section = Column(String(20), nullable=False, index=True)  # EquipmentCategory enum
    test_code = Column(String(50), nullable=True, index=True)  # Optional: specific test
    
    # QC requirements
    frequency = Column(String(20), nullable=False)  # QCFrequency enum
    validity_hours = Column(Integer, nullable=False, default=24)  # How long QC is valid
    
    # QC parameters
    parameter_name = Column(String(100), nullable=False)  # e.g., "Control Level 1"
    min_value = Column(DECIMAL(10, 3), nullable=True)
    max_value = Column(DECIMAL(10, 3), nullable=True)
    target_value = Column(DECIMAL(10, 3), nullable=True)
    
    # Rule status
    status = Column(String(20), nullable=False, default="ACTIVE")  # QCRuleStatus enum
    
    # Rule metadata
    description = Column(Text, nullable=True)
    created_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="qc_rules")
    created_by_user = relationship("User", foreign_keys=[created_by])
    qc_runs = relationship("QCRun", back_populates="qc_rule")
    
    def __repr__(self):
        return f"<QCRule(section='{self.section}', parameter='{self.parameter_name}')>"


class QCRun(BaseModel):
    """
    Quality Control Run - Records QC test execution and results
    """
    __tablename__ = "qc_runs"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # References
    equipment_id = Column(UUID_TYPE, ForeignKey("lab_equipment.id"), nullable=False, index=True)
    qc_rule_id = Column(UUID_TYPE, ForeignKey("qc_rules.id"), nullable=False, index=True)
    
    # Run details
    section = Column(String(20), nullable=False, index=True)  # EquipmentCategory enum
    run_at = Column(DateTime(timezone=True), nullable=False, index=True)
    run_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    
    # QC results
    status = Column(String(20), nullable=False)  # QCStatus enum
    values = Column(JSON_TYPE, nullable=True, default=lambda: {})  # QC parameter values
    
    # Run metadata
    batch_number = Column(String(100), nullable=True)  # QC material batch
    lot_number = Column(String(100), nullable=True)  # QC material lot
    remarks = Column(Text, nullable=True)
    
    # Validity tracking
    valid_until = Column(DateTime(timezone=True), nullable=True)  # Calculated based on rule
    
    # Deviation (when values outside rule min/max)
    deviation_notes = Column(Text, nullable=True)  # Auto-set when FAIL; describes deviation
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="qc_runs")
    equipment = relationship("Equipment", back_populates="qc_runs")
    qc_rule = relationship("QCRule", back_populates="qc_runs")
    run_by_user = relationship("User", foreign_keys=[run_by])
    corrective_actions = relationship("QCCorrectiveAction", back_populates="qc_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QCRun(section='{self.section}', status='{self.status}', run_at='{self.run_at}')>"


class QCCorrectiveAction(BaseModel):
    """
    Corrective action log - Records actions taken when QC fails.
    """
    __tablename__ = "qc_corrective_actions"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    qc_run_id = Column(UUID_TYPE, ForeignKey("qc_runs.id"), nullable=False, index=True)
    action_taken = Column(Text, nullable=False)  # Description of corrective action
    performed_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    qc_run = relationship("QCRun", back_populates="corrective_actions")
    performed_by_user = relationship("User", foreign_keys=[performed_by])


# ============================================================================
# REPORT SHARING & NOTIFICATION MODELS
# ============================================================================

class ReportShareToken(BaseModel):
    """
    Secure share tokens for lab reports - enables time-limited access
    """
    __tablename__ = "report_share_tokens"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # References
    lab_order_id = Column(UUID_TYPE, ForeignKey("lab_orders.id"), nullable=False, index=True)
    lab_report_id = Column(UUID_TYPE, ForeignKey("lab_reports.id"), nullable=False, index=True)
    
    # Token details
    token = Column(String(255), nullable=False, unique=True, index=True)  # Hashed token
    token_hash = Column(String(255), nullable=False)  # Additional security
    
    # Access control
    allowed_viewer_type = Column(String(20), nullable=False, default="PUBLIC")  # ViewerType enum
    specific_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)  # Optional specific user
    
    # Validity
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Revocation
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    revocation_reason = Column(Text, nullable=True)
    
    # Usage tracking
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_ip = Column(String(45), nullable=True)  # IPv6 support
    
    # Creation details
    created_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="report_share_tokens")
    lab_order = relationship("LabOrder", back_populates="share_tokens")
    lab_report = relationship("LabReport", back_populates="share_tokens")
    created_by_user = relationship("User", foreign_keys=[created_by])
    revoked_by_user = relationship("User", foreign_keys=[revoked_by])
    specific_user = relationship("User", foreign_keys=[specific_user_id])
    
    def __repr__(self):
        return f"<ReportShareToken(token='{self.token[:8]}...', expires_at='{self.expires_at}')>"


class NotificationOutbox(BaseModel):
    """
    Notification outbox for lab report notifications
    """
    __tablename__ = "notification_outbox"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(30), nullable=False, index=True)  # NotificationEventType enum
    event_id = Column(String(100), nullable=False, index=True)  # Reference ID (order_id, report_id, etc.)
    
    # Recipient details
    recipient_type = Column(String(20), nullable=False)  # PATIENT, DOCTOR, etc.
    recipient_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=True)
    recipient_phone = Column(String(20), nullable=True)
    
    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON_TYPE, nullable=True, default=lambda: {})  # Additional data (report_id, share_link, etc.)
    
    # Delivery details
    channel = Column(String(20), nullable=False, default="EMAIL")  # NotificationChannel enum
    status = Column(String(20), nullable=False, default="PENDING")  # NotificationStatus enum
    
    # Delivery tracking
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    
    # External service tracking
    external_id = Column(String(255), nullable=True)  # SMS/Email service message ID
    external_status = Column(String(50), nullable=True)  # External service status
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # For delayed notifications
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="notifications")
    recipient = relationship("User", foreign_keys=[recipient_id])
    
    def __repr__(self):
        return f"<NotificationOutbox(event_type='{self.event_type}', recipient='{self.recipient_id}', status='{self.status}')>"


class ReportAccess(BaseModel):
    """
    Audit log for report access tracking
    """
    __tablename__ = "report_access_logs"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # References
    lab_report_id = Column(UUID_TYPE, ForeignKey("lab_reports.id"), nullable=False, index=True)
    lab_order_id = Column(UUID_TYPE, ForeignKey("lab_orders.id"), nullable=False, index=True)
    
    # Access details
    accessed_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)  # Null for anonymous access
    access_method = Column(String(20), nullable=False)  # DIRECT, SHARE_TOKEN, API
    share_token_id = Column(UUID_TYPE, ForeignKey("report_share_tokens.id"), nullable=True)
    
    # Access metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    access_type = Column(String(20), nullable=False)  # VIEW, DOWNLOAD
    
    # Patient context (for RBAC validation)
    patient_id = Column(String(50), nullable=False, index=True)  # Patient reference
    
    # Timestamps
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="report_access_logs")
    lab_report = relationship("LabReport", back_populates="access_logs")
    lab_order = relationship("LabOrder", back_populates="access_logs")
    accessed_by_user = relationship("User", foreign_keys=[accessed_by])
    share_token = relationship("ReportShareToken", foreign_keys=[share_token_id])
    
    def __repr__(self):
        return f"<ReportAccess(report_id='{self.lab_report_id}', accessed_by='{self.accessed_by}', accessed_at='{self.accessed_at}')>"


# ============================================================================
# AUDIT TRAIL & COMPLIANCE MODELS
# ============================================================================

class LabAuditLog(BaseModel):
    """
    Comprehensive audit trail for NABL/CAP compliance
    Records all critical actions in the lab system
    """
    __tablename__ = "lab_audit_logs"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # Entity being audited
    entity_type = Column(String(20), nullable=False, index=True)  # AuditEntityType enum
    entity_id = Column(String(100), nullable=False, index=True)  # UUID or reference ID
    
    # Action details
    action = Column(String(20), nullable=False, index=True)  # AuditAction enum
    performed_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Change tracking
    old_value = Column(JSON_TYPE, nullable=True, default=lambda: {})  # Previous state (for updates)
    new_value = Column(JSON_TYPE, nullable=True, default=lambda: {})  # New state
    
    # Context information
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Additional details
    remarks = Column(Text, nullable=True)  # Human-readable description
    reference_id = Column(String(100), nullable=True)  # Related entity ID
    
    # Compliance flags
    is_critical = Column(Boolean, nullable=False, default=False)  # Critical for compliance
    requires_approval = Column(Boolean, nullable=False, default=False)  # Needs supervisor approval
    
    # Timestamps (immutable)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="lab_audit_logs")
    performed_by_user = relationship("User", foreign_keys=[performed_by])
    
    def __repr__(self):
        return f"<LabAuditLog(entity='{self.entity_type}:{self.entity_id}', action='{self.action}', by='{self.performed_by}')>"


class ChainOfCustody(BaseModel):
    """
    Sample chain of custody tracking for NABL/CAP compliance
    Tracks every movement and handling of samples
    """
    __tablename__ = "chain_of_custody"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # Sample reference
    sample_id = Column(UUID_TYPE, ForeignKey("lab_samples.id"), nullable=False, index=True)
    sample_no = Column(String(50), nullable=False, index=True)  # For quick reference
    
    # Custody event
    event_type = Column(String(20), nullable=False)  # COLLECTED, RECEIVED, PROCESSED, STORED, etc.
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Personnel involved
    from_user = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)  # Who handed over
    to_user = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)  # Who received
    
    # Location tracking
    from_location = Column(String(100), nullable=True)  # Previous location
    to_location = Column(String(100), nullable=False)  # Current location
    
    # Equipment involved (if applicable)
    equipment_id = Column(UUID_TYPE, ForeignKey("lab_equipment.id"), nullable=True)
    
    # Environmental conditions
    temperature = Column(DECIMAL(5, 2), nullable=True)  # Storage temperature
    humidity = Column(DECIMAL(5, 2), nullable=True)  # Storage humidity
    
    # Documentation
    remarks = Column(Text, nullable=True)
    witness_signature = Column(String(255), nullable=True)  # Digital signature reference
    
    # Integrity checks
    seal_number = Column(String(50), nullable=True)  # Tamper-evident seal
    condition_on_receipt = Column(String(20), nullable=True)  # GOOD, DAMAGED, LEAKED, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="chain_of_custody")
    sample = relationship("Sample", back_populates="custody_chain")
    from_user_rel = relationship("User", foreign_keys=[from_user])
    to_user_rel = relationship("User", foreign_keys=[to_user])
    equipment = relationship("Equipment", foreign_keys=[equipment_id])
    
    def __repr__(self):
        return f"<ChainOfCustody(sample='{self.sample_no}', event='{self.event_type}', timestamp='{self.event_timestamp}')>"


class ComplianceExport(BaseModel):
    """
    Tracks compliance exports for audit purposes
    """
    __tablename__ = "compliance_exports"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    # Export details
    export_type = Column(String(50), nullable=False, index=True)  # QC_LOGS, SAMPLE_REJECTIONS, etc.
    export_format = Column(String(10), nullable=False)  # CSV, PDF, EXCEL
    
    # Date range
    from_date = Column(DateTime(timezone=True), nullable=False)
    to_date = Column(DateTime(timezone=True), nullable=False)
    
    # Filters applied
    filters = Column(JSON_TYPE, nullable=True, default=lambda: {})  # Store filter criteria
    
    # Export metadata
    record_count = Column(Integer, nullable=False, default=0)
    file_size_bytes = Column(Integer, nullable=True)
    file_path = Column(String(500), nullable=True)  # Storage path
    file_hash = Column(String(64), nullable=True)  # SHA256 for integrity
    
    # User context
    exported_by = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    export_reason = Column(Text, nullable=True)  # Why was this exported
    
    # Status
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # File retention
    
    # Relationships
    hospital = relationship("Hospital", back_populates="compliance_exports")
    exported_by_user = relationship("User", foreign_keys=[exported_by])
    
    def __repr__(self):
        return f"<ComplianceExport(type='{self.export_type}', format='{self.export_format}', by='{self.exported_by}')>"