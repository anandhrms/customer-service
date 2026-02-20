import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import config
from core.library import logger


def send_email(subject: str, recipient_email: str | list[str], body: str):
    if isinstance(recipient_email, list):
        recipient_email = ", ".join(recipient_email)

    msg = MIMEMultipart()
    msg["From"] = config.MAIL_FROM_ADDRESS
    msg["To"] = recipient_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))
    try:
        with smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT) as server:
            server.starttls()
            server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logger.error(str(e))
