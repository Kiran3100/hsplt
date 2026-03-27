from typing import Optional, List
from decimal import Decimal
from datetime import date
from pydantic import BaseModel, Field


class RevenueReportRequest(BaseModel):
    """Schema for revenue report request"""
    start_date: date
    end_date: date
    report_type: str = Field(..., pattern="^(daily|monthly|yearly)$")


class RevenueReportResponse(BaseModel):
    """Schema for revenue report response"""
    period_start: date
    period_end: date
    total_revenue: Decimal
    total_opd_revenue: Decimal
    total_ipd_revenue: Decimal
    total_payments: Decimal
    outstanding_amount: Decimal


class OutstandingPaymentItem(BaseModel):
    """Schema for outstanding payment item"""
    bill_id: int
    bill_number: str
    bill_type: str
    patient_id: int
    patient_name: str
    bill_date: date
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    days_outstanding: int


class OutstandingPaymentsReportResponse(BaseModel):
    """Schema for outstanding payments report"""
    total_outstanding: Decimal
    bills: List[OutstandingPaymentItem]


class DepartmentRevenueItem(BaseModel):
    """Schema for department revenue item"""
    department_id: int
    department_name: str
    revenue: Decimal
    bill_count: int


class DepartmentRevenueReportResponse(BaseModel):
    """Schema for department revenue report"""
    period_start: date
    period_end: date
    total_revenue: Decimal
    departments: List[DepartmentRevenueItem]


class DoctorRevenueItem(BaseModel):
    """Schema for doctor revenue item"""
    doctor_id: int
    doctor_name: str
    revenue: Decimal
    patient_count: int
    bill_count: int


class DoctorRevenueReportResponse(BaseModel):
    """Schema for doctor revenue report"""
    period_start: date
    period_end: date
    total_revenue: Decimal
    doctors: List[DoctorRevenueItem]


class TaxReportItem(BaseModel):
    """Schema for tax report item"""
    tax_name: str
    tax_percentage: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal


class TaxReportResponse(BaseModel):
    """Schema for tax report"""
    period_start: date
    period_end: date
    total_taxable_amount: Decimal
    total_tax_amount: Decimal
    taxes: List[TaxReportItem]
