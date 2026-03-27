"""
Generate payment receipt PDF (ReportLab).
Receipt includes: hospital info, patient, bill number, payment method, amount, date.
"""
import io
from datetime import datetime
from typing import Optional, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _str(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, datetime):
        return v.strftime("%d-%b-%Y %H:%M")
    return str(v).strip() or "—"


def build_receipt_pdf(
    payment: Any,
    bill: Any,
    patient: Optional[Any],
    hospital: Optional[Any],
    receipt_number: Optional[str] = None,
) -> bytes:
    """
    Build receipt PDF bytes.
    payment, bill: required (SQLAlchemy models or dict-like).
    patient, hospital: optional (for display).
    receipt_number: optional receipt number to show.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 40 * mm
    line_height = 6 * mm

    # Hospital
    if hospital:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(20 * mm, y, _str(getattr(hospital, "name", None)))
        y -= line_height
        c.setFont("Helvetica", 9)
        addr = _str(getattr(hospital, "address", None))
        if addr:
            c.drawString(20 * mm, y, addr[:80])
            y -= line_height
        c.drawString(20 * mm, y, f"{_str(getattr(hospital, 'city', None))} {_str(getattr(hospital, 'pincode', None))} — {_str(getattr(hospital, 'phone', None))}")
        y -= line_height * 1.5
    else:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, "Payment Receipt")
        y -= line_height * 1.5

    # Title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "PAYMENT RECEIPT")
    y -= line_height * 1.5

    # Receipt number
    if receipt_number:
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, y, f"Receipt No.: {receipt_number}")
        y -= line_height

    # Bill & Patient
    c.setFont("Helvetica", 10)
    bill_no = _str(getattr(bill, "bill_number", None))
    c.drawString(20 * mm, y, f"Bill No.: {bill_no}")
    y -= line_height
    if patient:
        pid = getattr(patient, "patient_id", None)
        mrn = getattr(patient, "mrn", None)
        name = f"Patient ID: {_str(pid)}" + (f" (MRN: {_str(mrn)})" if mrn else "")
        c.drawString(20 * mm, y, f"Patient: {name}")
        y -= line_height
    y -= line_height * 0.5

    # Payment details
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Payment details")
    y -= line_height
    c.setFont("Helvetica", 10)
    amount = getattr(payment, "amount", 0)
    if hasattr(amount, "__float__"):
        amount = f"{float(amount):,.2f}"
    else:
        amount = str(amount)
    currency = _str(getattr(payment, "currency", "INR"))
    c.drawString(20 * mm, y, f"Amount: {currency} {amount}")
    y -= line_height
    c.drawString(20 * mm, y, f"Method: {_str(getattr(payment, 'method', None))}")
    y -= line_height
    if getattr(payment, "provider", None):
        c.drawString(20 * mm, y, f"Provider: {_str(payment.provider)}")
        y -= line_height
    paid_at = getattr(payment, "paid_at", None) or getattr(payment, "created_at", None)
    c.drawString(20 * mm, y, f"Date: {_str(paid_at)}")
    y -= line_height
    if getattr(payment, "transaction_id", None):
        c.drawString(20 * mm, y, f"Transaction ID: {_str(payment.transaction_id)}")
        y -= line_height

    # Footer
    y = 25 * mm
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, y, "This is a computer-generated receipt.")
    c.drawString(20 * mm, y - line_height * 0.8, f"Generated at {datetime.utcnow().strftime('%d-%b-%Y %H:%M UTC')}")

    c.save()
    buf.seek(0)
    return buf.read()
