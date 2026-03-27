import smtplib, ssl
from email.message import EmailMessage
from app.core.config import settings


def send_pdf_email(to_email: str, subject: str, body: str, pdf_bytes: bytes, filename: str):
    msg = EmailMessage()
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=filename
    )

    context = ssl.create_default_context()

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        # 🔥 REQUIRED: perform handshake BEFORE TLS
        server.ehlo()

        # Upgrade to TLS
        server.starttls(context=context)

        # 🔥 REQUIRED: handshake again AFTER TLS
        server.ehlo()

        # Login
        server.login(settings.SMTP_USER, settings.SMTP_PASS)

        # Send
        server.send_message(msg)
