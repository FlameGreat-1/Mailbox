import smtplib
import logging
from typing import Optional, List, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, formatdate
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)


class SMTPProvider:
    def __init__(self, connection: smtplib.SMTP):
        self._connection = connection

    @property
    def connection(self) -> smtplib.SMTP:
        return self._connection

    def send_email(
        self,
        from_email: str,
        to_emails: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        from_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        try:
            if body_html or attachments:
                msg = MIMEMultipart("alternative")
            else:
                msg = MIMEMultipart()

            if from_name:
                msg["From"] = formataddr((from_name, from_email))
            else:
                msg["From"] = from_email

            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)

            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

            if reply_to:
                msg["Reply-To"] = reply_to

            msg["X-Mailer"] = f"{settings.app.app_name}/{settings.app.version}"

            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

            if attachments:
                for file_path in attachments:
                    attachment = self._create_attachment(file_path)
                    if attachment:
                        msg.attach(attachment)

            all_recipients = list(to_emails)
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)

            self._connection.sendmail(from_email, all_recipients, msg.as_string())

            logger.info(f"Email sent successfully to {', '.join(to_emails)}")
            return True, "Email sent successfully"

        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipients refused: {e}"
            logger.error(error_msg)
            return False, error_msg

        except smtplib.SMTPSenderRefused as e:
            error_msg = f"Sender refused: {e}"
            logger.error(error_msg)
            return False, error_msg

        except smtplib.SMTPDataError as e:
            error_msg = f"SMTP data error: {e}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def send_reply(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body_text: str,
        original_message_id: str,
        body_html: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        from_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        try:
            if body_html:
                msg = MIMEMultipart("alternative")
            else:
                msg = MIMEMultipart()

            if from_name:
                msg["From"] = formataddr((from_name, from_email))
            else:
                msg["From"] = from_email

            msg["To"] = to_email
            msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
            msg["Date"] = formatdate(localtime=True)
            msg["In-Reply-To"] = original_message_id
            msg["References"] = original_message_id

            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

            msg["X-Mailer"] = f"{settings.app.app_name}/{settings.app.version}"

            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

            all_recipients = [to_email]
            if cc_emails:
                all_recipients.extend(cc_emails)

            self._connection.sendmail(from_email, all_recipients, msg.as_string())

            logger.info(f"Reply sent successfully to {to_email}")
            return True, "Reply sent successfully"

        except Exception as e:
            error_msg = f"Failed to send reply: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _create_attachment(self, file_path: str) -> Optional[MIMEBase]:
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Attachment file not found: {file_path}")
            return None

        try:
            with open(path, "rb") as f:
                file_data = f.read()

            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(file_data)
            encoders.encode_base64(attachment)

            attachment.add_header(
                "Content-Disposition",
                f"attachment; filename={path.name}",
            )

            return attachment

        except Exception as e:
            logger.error(f"Failed to create attachment from {file_path}: {e}")
            return None

    def verify_connection(self) -> bool:
        try:
            self._connection.noop()
            return True
        except Exception:
            return False
