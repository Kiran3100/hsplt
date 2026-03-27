"""
Pharmacy Module Domain Exceptions
Specific error codes and messages for pharmacy operations.
"""
from fastapi import HTTPException, status


class PharmacyException(HTTPException):
    """Base exception for pharmacy module"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class OutOfStockError(PharmacyException):
    """Raised when attempting to sell more than available stock"""
    def __init__(self, medicine_name: str, requested: float, available: float):
        super().__init__(
            detail=f"Insufficient stock for {medicine_name}. Requested: {requested}, Available: {available}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class BatchExpiredError(PharmacyException):
    """Raised when attempting to sell from expired batch"""
    def __init__(self, batch_no: str, expiry_date: str):
        super().__init__(
            detail=f"Cannot sell from expired batch {batch_no} (expired on {expiry_date})",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class TenantViolationError(PharmacyException):
    """Raised when cross-hospital access is attempted"""
    def __init__(self, resource_type: str):
        super().__init__(
            detail=f"Access denied: {resource_type} belongs to different hospital",
            status_code=status.HTTP_403_FORBIDDEN
        )


class DuplicateSaleError(PharmacyException):
    """Raised when duplicate sale is detected via idempotency key"""
    def __init__(self, sale_number: str):
        super().__init__(
            detail=f"Duplicate sale detected: {sale_number}",
            status_code=status.HTTP_409_CONFLICT
        )


class InvalidPOStatusError(PharmacyException):
    """Raised when PO operation is invalid for current status"""
    def __init__(self, operation: str, current_status: str):
        super().__init__(
            detail=f"Cannot {operation} purchase order in {current_status} status",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class GRNAlreadyFinalizedError(PharmacyException):
    """Raised when attempting to modify finalized GRN"""
    def __init__(self, grn_number: str):
        super().__init__(
            detail=f"GRN {grn_number} is already finalized and cannot be modified",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class EmptyGRNError(PharmacyException):
    """Raised when attempting to finalize GRN without items"""
    def __init__(self):
        super().__init__(
            detail="Cannot finalize GRN without items",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class NegativeStockError(PharmacyException):
    """Raised when stock operation would result in negative quantity"""
    def __init__(self, batch_no: str):
        super().__init__(
            detail=f"Operation would result in negative stock for batch {batch_no}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PrescriptionRequiredError(PharmacyException):
    """Raised when prescription is required but not provided"""
    def __init__(self, medicine_name: str):
        super().__init__(
            detail=f"Prescription required for {medicine_name}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InvalidBatchSelectionError(PharmacyException):
    """Raised when selected batch is invalid"""
    def __init__(self, reason: str):
        super().__init__(
            detail=f"Invalid batch selection: {reason}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class SaleAlreadyCompletedError(PharmacyException):
    """Raised when attempting to modify completed sale"""
    def __init__(self, sale_number: str):
        super().__init__(
            detail=f"Sale {sale_number} is already completed and cannot be modified",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InvalidReturnError(PharmacyException):
    """Raised when return operation is invalid"""
    def __init__(self, reason: str):
        super().__init__(
            detail=f"Invalid return: {reason}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class MedicineNotFoundError(PharmacyException):
    """Raised when medicine is not found"""
    def __init__(self, medicine_id: str):
        super().__init__(
            detail=f"Medicine not found: {medicine_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )


class SupplierNotFoundError(PharmacyException):
    """Raised when supplier is not found"""
    def __init__(self, supplier_id: str):
        super().__init__(
            detail=f"Supplier not found: {supplier_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )


class PurchaseOrderNotFoundError(PharmacyException):
    """Raised when purchase order is not found"""
    def __init__(self, po_id: str):
        super().__init__(
            detail=f"Purchase order not found: {po_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )


class GRNNotFoundError(PharmacyException):
    """Raised when GRN is not found"""
    def __init__(self, grn_id: str):
        super().__init__(
            detail=f"GRN not found: {grn_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )


class SaleNotFoundError(PharmacyException):
    """Raised when sale is not found"""
    def __init__(self, sale_id: str):
        super().__init__(
            detail=f"Sale not found: {sale_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )


class StockBatchNotFoundError(PharmacyException):
    """Raised when stock batch is not found"""
    def __init__(self, batch_id: str):
        super().__init__(
            detail=f"Stock batch not found: {batch_id}",
            status_code=status.HTTP_404_NOT_FOUND
        )
