import imaplib
import smtplib
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from src.config import settings
from src.auth.encryption import encrypt, decrypt
from src.database.models import Credential, AuthType
from src.database.repositories import CredentialsRepository

logger = logging.getLogger(__name__)


@dataclass
class AppPasswordSession:
    email: str
    imap_connection: Optional[imaplib.IMAP4_SSL] = None
    smtp_connection: Optional[smtplib.SMTP] = None
    is_authenticated: bool = False


class AppPasswordHandler:
    def __init__(self):
        self._session: Optional[AppPasswordSession] = None

    @property
    def session(self) -> Optional[AppPasswordSession]:
        return self._session

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None and self._session.is_authenticated

    @property
    def current_email(self) -> Optional[str]:
        return self._session.email if self._session else None

    def authenticate(self, email: str, app_password: str) -> Tuple[bool, str]:
        try:
            imap_conn = self._connect_imap(email, app_password)
            if not imap_conn:
                return False, "Failed to connect to Gmail IMAP server"

            self._session = AppPasswordSession(
                email=email,
                imap_connection=imap_conn,
                is_authenticated=True,
            )

            self._store_credentials(email, app_password)

            logger.info(f"Successfully authenticated: {email}")
            return True, "Authentication successful"

        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "AUTHENTICATIONFAILED" in error_msg.upper():
                return False, "Invalid email or app password"
            return False, f"IMAP authentication error: {error_msg}"

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False, f"Authentication failed: {str(e)}"

    def authenticate_from_stored(self) -> Tuple[bool, str]:
        credential = CredentialsRepository.find_first()

        if not credential:
            return False, "No stored credentials found"

        if credential.auth_type != AuthType.APP_PASSWORD:
            return False, "Stored credential is not app password type"

        try:
            app_password = decrypt(credential.encrypted_token)
            return self.authenticate(credential.user_email, app_password)

        except ValueError as e:
            logger.error(f"Failed to decrypt stored credentials: {e}")
            return False, "Failed to decrypt stored credentials"

    def _connect_imap(self, email: str, app_password: str) -> Optional[imaplib.IMAP4_SSL]:
        try:
            imap = imaplib.IMAP4_SSL(
                settings.email.imap_host,
                settings.email.imap_port,
            )
            imap.login(email, app_password)
            return imap

        except imaplib.IMAP4.error:
            raise
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return None

    def get_smtp_connection(self) -> Optional[smtplib.SMTP]:
        if not self._session or not self._session.is_authenticated:
            return None

        if self._session.smtp_connection:
            try:
                self._session.smtp_connection.noop()
                return self._session.smtp_connection
            except Exception:
                self._session.smtp_connection = None

        credential = CredentialsRepository.find_by_email(self._session.email)
        if not credential:
            return None

        try:
            app_password = decrypt(credential.encrypted_token)
            smtp = smtplib.SMTP(settings.email.smtp_host, settings.email.smtp_port)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self._session.email, app_password)

            self._session.smtp_connection = smtp
            return smtp

        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            return None

    def get_imap_connection(self) -> Optional[imaplib.IMAP4_SSL]:
        if not self._session or not self._session.is_authenticated:
            return None

        if self._session.imap_connection:
            try:
                self._session.imap_connection.noop()
                return self._session.imap_connection
            except Exception:
                self._session.imap_connection = None

        credential = CredentialsRepository.find_by_email(self._session.email)
        if not credential:
            return None

        try:
            app_password = decrypt(credential.encrypted_token)
            imap = self._connect_imap(self._session.email, app_password)
            self._session.imap_connection = imap
            return imap

        except Exception as e:
            logger.error(f"IMAP reconnection failed: {e}")
            return None

    def _store_credentials(self, email: str, app_password: str) -> None:
        encrypted_password = encrypt(app_password)

        credential = Credential(
            user_email=email,
            auth_type=AuthType.APP_PASSWORD,
            encrypted_token=encrypted_password,
        )

        CredentialsRepository.upsert(credential)
        logger.info(f"Credentials stored for: {email}")

    def logout(self) -> None:
        if self._session:
            if self._session.imap_connection:
                try:
                    self._session.imap_connection.logout()
                except Exception:
                    pass

            if self._session.smtp_connection:
                try:
                    self._session.smtp_connection.quit()
                except Exception:
                    pass

            self._session = None
            logger.info("Logged out successfully")

    def delete_stored_credentials(self, email: str) -> bool:
        return CredentialsRepository.delete_by_email(email)

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
