import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    pass


def send_briefing(html_body, config):
    email_cfg = config["email"]
    subject_prefix = email_cfg.get("subject_prefix", "每日简报")
    date_str = datetime.now().strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{subject_prefix} — {date_str}"
    msg["From"] = email_cfg["sender"]
    msg["To"] = email_cfg["recipient"]

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        smtp_server = email_cfg["smtp_server"]
        smtp_port = email_cfg["smtp_port"]

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.starttls()

        server.login(email_cfg["sender"], email_cfg["password"])
        server.sendmail(email_cfg["sender"], [email_cfg["recipient"]], msg.as_string())
        server.quit()

        logger.info("Email sent successfully to %s", email_cfg["recipient"])
        return True
    except smtplib.SMTPException as e:
        raise EmailSendError(f"SMTP error: {e}")
    except Exception as e:
        raise EmailSendError(f"Failed to send email: {e}")
