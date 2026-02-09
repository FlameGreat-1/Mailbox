import logging
import imaplib
import smtplib
from typing import Optional, Tuple
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import settings
from src.auth.encryption import encrypt, decrypt
from src.database.models import Credential, AuthType
from src.database.repositories import CredentialsRepository

logger = logging.getLogger(__name__)


@dataclass
class ZohoSession:
    email: str
    password: str
    imap_connection: Optional[imaplib.IMAP4_SSL] = None
    smtp_connection: Optional[smtplib.SMTP_SSL] = None
    is_authenticated: bool = False


class ZohoMailHandler:
    def __init__(self):
        self._session: Optional[ZohoSession] = None

    @property
    def session(self) -> Optional[ZohoSession]:
        return self._session

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None and self._session.is_authenticated

    @property
    def current_email(self) -> Optional[str]:
        return self._session.email if self._session else None

    def authenticate(self, email: str, password: str) -> Tuple[bool, str]:
        if not email or not password:
            return False, "Email and password are required"

        if not self._validate_email_format(email):
            return False, "Invalid email format"

        try:
            imap_conn = self._connect_imap(email, password)
            smtp_conn = self._connect_smtp(email, password)

            self._session = ZohoSession(
                email=email,
                password=password,
                imap_connection=imap_conn,
                smtp_connection=smtp_conn,
                is_authenticated=True,
            )

            self._store_credentials(email, password)

            logger.info(f"Successfully authenticated Zoho Mail: {email}")
            return True, f"Authentication successful for {email}"

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP authentication failed for {email}: {e}")
            return False, f"IMAP authentication failed: Invalid credentials"

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed for {email}: {e}")
            return False, f"SMTP authentication failed: Invalid credentials"

        except Exception as e:
            logger.error(f"Zoho authentication failed for {email}: {e}")
            return False, f"Authentication failed: {str(e)}"

    def authenticate_from_stored(self, email: str) -> Tuple[bool, str]:
        credential = CredentialsRepository.find_by_email(email)

        if not credential:
            return False, f"No stored credentials found for {email}"

        if credential.auth_type != AuthType.ZOHO:
            return False, "Stored credential is not Zoho type"

        try:
            password = decrypt(credential.encrypted_token)

            imap_conn = self._connect_imap(credential.user_email, password)
            smtp_conn = self._connect_smtp(credential.user_email, password)

            self._session = ZohoSession(
                email=credential.user_email,
                password=password,
                imap_connection=imap_conn,
                smtp_connection=smtp_conn,
                is_authenticated=True,
            )

            logger.info(f"Restored Zoho session for: {credential.user_email}")
            return True, f"Session restored for {credential.user_email}"

        except Exception as e:
            logger.error(f"Failed to restore Zoho session: {e}")
            return False, f"Failed to restore session: {str(e)}"

    def get_imap_connection(self) -> Optional[imaplib.IMAP4_SSL]:
        if not self._session or not self._session.is_authenticated:
            return None

        try:
            self._session.imap_connection.noop()
            return self._session.imap_connection
        except:
            try:
                self._session.imap_connection = self._connect_imap(
                    self._session.email,
                    self._session.password
                )
                return self._session.imap_connection
            except Exception as e:
                logger.error(f"Failed to reconnect IMAP: {e}")
                return None

    def get_smtp_connection(self) -> Optional[smtplib.SMTP_SSL]:
        if not self._session or not self._session.is_authenticated:
            return None

        try:
            self._session.smtp_connection.noop()
            return self._session.smtp_connection
        except:
            try:
                self._session.smtp_connection = self._connect_smtp(
                    self._session.email,
                    self._session.password
                )
                return self._session.smtp_connection
            except Exception as e:
                logger.error(f"Failed to reconnect SMTP: {e}")
                return None

    def _connect_imap(self, email: str, password: str) -> imaplib.IMAP4_SSL:
        try:
            imap = imaplib.IMAP4_SSL(
                settings.zoho.imap_host,
                settings.zoho.imap_port,
                timeout=settings.zoho.connection_timeout
            )
            imap.login(email, password)
            return imap
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            raise

    def _connect_smtp(self, email: str, password: str) -> smtplib.SMTP_SSL:
        try:
            smtp = smtplib.SMTP_SSL(
                settings.zoho.smtp_host,
                settings.zoho.smtp_port,
                timeout=settings.zoho.connection_timeout
            )
            smtp.login(email, password)
            return smtp
        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            raise

    def _store_credentials(self, email: str, password: str) -> None:
        encrypted_password = encrypt(password)

        credential = Credential(
            user_email=email,
            auth_type=AuthType.ZOHO,
            encrypted_token=encrypted_password,
            access_token=None,
            token_expiry=None,
        )

        CredentialsRepository.upsert(credential)
        logger.info(f"Zoho credentials stored for: {email}")

    def _validate_email_format(self, email: str) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def verify_connection(self) -> bool:
        if not self._session or not self._session.is_authenticated:
            return False

        try:
            imap = self.get_imap_connection()
            if imap:
                imap.noop()
                return True
            return False
        except Exception:
            return False

    def logout(self) -> None:
        if self._session:
            try:
                if self._session.imap_connection:
                    self._session.imap_connection.logout()
            except:
                pass

            try:
                if self._session.smtp_connection:
                    self._session.smtp_connection.quit()
            except:
                pass

            self._session = None
            logger.info("Zoho session ended")

    def delete_stored_credentials(self, email: str) -> bool:
        return CredentialsRepository.delete_by_email(email)

    def send_test_email(self, to_email: str, subject: str = "Test Email") -> Tuple[bool, str]:
        if not self._session or not self._session.is_authenticated:
            return False, "Not authenticated"

        try:
            smtp = self.get_smtp_connection()
            if not smtp:
                return False, "SMTP connection unavailable"

            msg = MIMEMultipart()
            msg['From'] = self._session.email
            msg['To'] = to_email
            msg['Subject'] = subject

            body = "This is a test email from Zoho Mail integration."
            msg.attach(MIMEText(body, 'plain'))

            smtp.send_message(msg)
            logger.info(f"Test email sent to {to_email}")
            return True, f"Test email sent successfully to {to_email}"

        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            return False, f"Failed to send email: {str(e)}"
