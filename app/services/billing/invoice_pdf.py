"""
Generate bill invoice PDF (ReportLab).
Invoice includes: hospital info, patient, bill number, line items, totals, amount paid, balance due.
"""
import io
from datetime import datetime
from typing import Optional, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _str(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, datetime):
        return v.strftime("%d-%b-%Y %H:%M")
    return str(v).strip() or "—"


def _num(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def build_invoice_pdf(
    bill: Any,
    items: Optional[List[Any]] = None,
    patient: Optional[Any] = None,
    hospital: Optional[Any] = None,
) -> bytes:
    """
    Build invoice PDF bytes.
    bill: required (Bill model or dict-like).
    items: optional list of line items (BillItem); if None, uses getattr(bill, "items", []).
    patient, hospital: optional for display.
    """
    if items is None:
        items = list(getattr(bill, "items", []) or [])
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 35 * mm
    line_height = 5.5 * mm
    margin = 20 * mm
    col_desc = margin
    col_qty = width - 70 * mm
    col_price = width - 50 * mm
    col_total = width - 25 * mm

    # Hospital
    if hospital:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, _str(getattr(hospital, "name", None)))
        y -= line_height
        c.setFont("Helvetica", 9)
        for part in (_str(getattr(hospital, "address", None)), f"{_str(getattr(hospital, 'city', None))} {_str(getattr(hospital, 'pincode', None))}", _str(getattr(hospital, "phone", None))):
            if part and part != "—":
                c.drawString(margin, y, part[:70])
                y -= line_height
        y -= line_height * 0.5
    else:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, "INVOICE")
        y -= line_height * 1.5

    # Invoice title and bill info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "TAX INVOICE / BILL")
    y -= line_height
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Bill No.: {_str(getattr(bill, 'bill_number', None))}  |  Type: {_str(getattr(bill, 'bill_type', None))}  |  Status: {_str(getattr(bill, 'status', None))}")
    y -= line_height
    created = getattr(bill, "created_at", None) or getattr(bill, "finalized_at", None)
    c.drawString(margin, y, f"Date: {_str(created)}")
    y -= line_height
    if patient:
        pid = getattr(patient, "patient_id", None)
        mrn = getattr(patient, "mrn", None)
        c.drawString(margin, y, f"Patient: ID {_str(pid)}" + (f"  (MRN: {_str(mrn)})" if mrn else ""))
        y -= line_height
    y -= line_height * 0.5

    # Table header
    c.setFont("Helvetica-Bold", 9)
    c.drawString(col_desc, y, "Description")
    c.drawString(col_qty, y, "Qty")
    c.drawString(col_price, y, "Unit Price")
    c.drawString(col_total, y, "Total")
    y -= line_height
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.line(margin, y, width - margin, y)
    y -= line_height * 0.8

    # Line items
    c.setFont("Helvetica", 9)
    for it in items:
        desc = (getattr(it, "description", None) or "")[:45]
        qty = _num(getattr(it, "quantity", 1))
        up = _num(getattr(it, "unit_price", 0))
        lt = _num(getattr(it, "line_total", 0))
        c.drawString(col_desc, y, desc)
        c.drawString(col_qty, y, f"{qty:.2f}")
        c.drawString(col_price, y, f"{up:,.2f}")
        c.drawString(col_total, y, f"{lt:,.2f}")
        y -= line_height
        if y < 80 * mm:
            c.showPage()
            y = height - 25 * mm
            c.setFont("Helvetica", 9)

    y -= line_height * 0.5
    c.line(margin, y, width - margin, y)
    y -= line_height

    # Totals
    subtotal = _num(getattr(bill, "subtotal", 0))
    discount = _num(getattr(bill, "discount_amount", 0))
    tax = _num(getattr(bill, "tax_amount", 0))
    total = _num(getattr(bill, "total_amount", 0))
    amount_paid = _num(getattr(bill, "amount_paid", 0))
    balance_due = _num(getattr(bill, "balance_due", 0))
    c.drawString(col_price, y, "Subtotal:")
    c.drawString(col_total, y, f"{subtotal:,.2f}")
    y -= line_height
    if discount != 0:
        c.drawString(col_price, y, "Discount:")
        c.drawString(col_total, y, f"-{discount:,.2f}")
        y -= line_height
    c.drawString(col_price, y, "Tax:")
    c.drawString(col_total, y, f"{tax:,.2f}")
    y -= line_height
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col_price, y, "Total:")
    c.drawString(col_total, y, f"{total:,.2f}")
    y -= line_height
    c.setFont("Helvetica", 9)
    c.drawString(col_price, y, "Amount Paid:")
    c.drawString(col_total, y, f"{amount_paid:,.2f}")
    y -= line_height
    c.drawString(col_price, y, "Balance Due:")
    c.drawString(col_total, y, f"{balance_due:,.2f}")
    y -= line_height * 1.5

    # Footer
    y = min(y, 28 * mm)
    c.setFont("Helvetica", 8)
    c.drawString(margin, y, "This is a computer-generated invoice.")
    c.drawString(margin, y - line_height * 0.8, f"Generated at {datetime.utcnow().strftime('%d-%b-%Y %H:%M UTC')}")

    c.save()
    buf.seek(0)
    return buf.read()
