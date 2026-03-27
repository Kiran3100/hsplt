from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO

def generate_receipt_pdf(transaction, payment_attempt=None):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 800, "PAYMENT RECEIPT")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 770, f"Transaction ID: {transaction.id}")
    pdf.drawString(50, 750, f"Amount: {transaction.amount} {transaction.currency}")
    pdf.drawString(50, 730, f"Status: {transaction.status}")
    pdf.drawString(50, 710, f"Gateway: {transaction.gateway}")
    pdf.drawString(50, 690, f"External ID: {transaction.external_id}")

    if payment_attempt:
        pdf.drawString(50, 670, f"Payment Attempt ID: {payment_attempt.id}")
        pdf.drawString(50, 650, f"Raw Response: {str(payment_attempt.raw_response)[:80]}...")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer.getvalue()
