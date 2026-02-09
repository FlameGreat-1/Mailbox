import logging
from typing import Optional, Tuple
from enum import Enum

from src.database.models import AuthType, Credential
from src.database.repositories import CredentialsRepository
from src.auth.handlers.app_password import AppPasswordHandler
from src.auth.handlers.oauth import OAuthHandler
from src.auth.handlers.zoho_mail import ZohoMailHandler

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    APP_PASSWORD = "app_password"
    OAUTH = "oauth"
    ZOHO = "zoho"


class AuthManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._app_password_handler = AppPasswordHandler()
        self._oauth_handler = OAuthHandler()
        self._zoho_handler = ZohoMailHandler()
        self._active_method: Optional[AuthMethod] = None
        self._initialized = True

    @property
    def is_authenticated(self) -> bool:
        if self._active_method == AuthMethod.APP_PASSWORD:
            return self._app_password_handler.is_authenticated
        elif self._active_method == AuthMethod.OAUTH:
            return self._oauth_handler.is_authenticated
        elif self._active_method == AuthMethod.ZOHO:
            return self._zoho_handler.is_authenticated
        return False

    @property
    def current_email(self) -> Optional[str]:
        if self._active_method == AuthMethod.APP_PASSWORD:
            return self._app_password_handler.current_email
        elif self._active_method == AuthMethod.OAUTH:
            return self._oauth_handler.current_email
        elif self._active_method == AuthMethod.ZOHO:
            return self._zoho_handler.current_email
        return None

    @property
    def active_method(self) -> Optional[AuthMethod]:
        return self._active_method

    @property
    def app_password_handler(self) -> AppPasswordHandler:
        return self._app_password_handler

    @property
    def oauth_handler(self) -> OAuthHandler:
        return self._oauth_handler

    @property
    def zoho_handler(self) -> ZohoMailHandler:
        return self._zoho_handler

    def has_stored_credentials(self, email: Optional[str] = None) -> bool:
        """
        Check if credentials exist for a specific email.
        If email is None, checks if ANY credentials exist (for backward compatibility).
        """
        if email:
            return CredentialsRepository.find_by_email(email) is not None
        return CredentialsRepository.find_first() is not None

    def get_stored_auth_type(self, email: Optional[str] = None) -> Optional[AuthType]:
        """
        Get the auth type for a specific email.
        If email is None, gets the first credential's auth type (for backward compatibility).
        """
        if email:
            credential = CredentialsRepository.find_by_email(email)
        else:
            credential = CredentialsRepository.find_first()
        
        if credential:
            return credential.auth_type
        return None

    def authenticate_user_with_stored_credentials(self, email: str) -> Tuple[bool, str]:
        """
        Authenticate a specific user using their stored credentials.
        This is called AFTER the user enters their email on the login screen.
        """
        credential = CredentialsRepository.find_by_email(email)

        if not credential:
            return False, f"No stored credentials found for {email}"

        if credential.auth_type == AuthType.APP_PASSWORD:
            success, message = self._app_password_handler.authenticate_from_stored(email)
            if success:
                self._active_method = AuthMethod.APP_PASSWORD
            return success, message

        elif credential.auth_type == AuthType.OAUTH:
            success, message = self._oauth_handler.authenticate_from_stored(email)
            if success:
                self._active_method = AuthMethod.OAUTH
            return success, message

        elif credential.auth_type == AuthType.ZOHO:
            success, message = self._zoho_handler.authenticate_from_stored(email)
            if success:
                self._active_method = AuthMethod.ZOHO
            return success, message

        return False, "Unknown authentication type"

    def authenticate_with_app_password(self, email: str, app_password: str) -> Tuple[bool, str]:
        success, message = self._app_password_handler.authenticate(email, app_password)

        if success:
            self._active_method = AuthMethod.APP_PASSWORD

        return success, message

    def authenticate_with_oauth(self) -> Tuple[bool, str]:
        """
        Automatic OAuth authentication with callback server.
        Opens browser, waits for user authorization, captures code automatically.
        """
        success, message = self._oauth_handler.authenticate()

        if success:
            self._active_method = AuthMethod.OAUTH

        return success, message

    def authenticate_with_zoho(self, email: str, password: str) -> Tuple[bool, str]:
        success, message = self._zoho_handler.authenticate(email, password)

        if success:
            self._active_method = AuthMethod.ZOHO

        return success, message

    def has_oauth_client_secret(self) -> bool:
        return self._oauth_handler.has_client_secret()

    def get_gmail_service(self):
        if self._active_method == AuthMethod.OAUTH:
            return self._oauth_handler.get_gmail_service()
        return None

    def get_calendar_service(self):
        if self._active_method == AuthMethod.OAUTH:
            return self._oauth_handler.get_calendar_service()
        return None

    def get_imap_connection(self):
        if self._active_method == AuthMethod.APP_PASSWORD:
            return self._app_password_handler.get_imap_connection()
        elif self._active_method == AuthMethod.ZOHO:
            return self._zoho_handler.get_imap_connection()
        return None

    def get_smtp_connection(self):
        if self._active_method == AuthMethod.APP_PASSWORD:
            return self._app_password_handler.get_smtp_connection()
        elif self._active_method == AuthMethod.ZOHO:
            return self._zoho_handler.get_smtp_connection()
        return None

    def verify_connection(self) -> bool:
        if self._active_method == AuthMethod.APP_PASSWORD:
            return self._app_password_handler.verify_connection()
        elif self._active_method == AuthMethod.OAUTH:
            return self._oauth_handler.verify_connection()
        elif self._active_method == AuthMethod.ZOHO:
            return self._zoho_handler.verify_connection()
        return False

    def logout(self) -> None:
        if self._active_method == AuthMethod.APP_PASSWORD:
            self._app_password_handler.logout()
        elif self._active_method == AuthMethod.OAUTH:
            self._oauth_handler.logout()
        elif self._active_method == AuthMethod.ZOHO:
            self._zoho_handler.logout()

        self._active_method = None
        logger.info("User logged out")

    def logout_and_clear(self) -> bool:
        email = self.current_email

        self.logout()

        if email:
            CredentialsRepository.delete_by_email(email)
            logger.info(f"Credentials cleared for: {email}")
            return True

        return False


_auth_manager = None


def get_auth_manager() -> AuthManager:
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
