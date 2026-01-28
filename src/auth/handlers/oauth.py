import os
import json
import logging
import webbrowser
from typing import Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build, Resource

from src.config import settings
from src.auth.encryption import encrypt, decrypt
from src.database.models import Credential, AuthType
from src.database.repositories import CredentialsRepository

logger = logging.getLogger(__name__)

CREDENTIALS_DIR = Path(__file__).parent.parent.parent.parent / "credentials"
CLIENT_SECRET_FILE = CREDENTIALS_DIR / "client_secret.json"


@dataclass
class OAuthSession:
    email: str
    credentials: Credentials
    gmail_service: Optional[Resource] = None
    calendar_service: Optional[Resource] = None
    is_authenticated: bool = False


class OAuthHandler:
    def __init__(self):
        self._session: Optional[OAuthSession] = None
        self._flow: Optional[Flow] = None

    @property
    def session(self) -> Optional[OAuthSession]:
        return self._session

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None and self._session.is_authenticated

    @property
    def current_email(self) -> Optional[str]:
        return self._session.email if self._session else None

    def has_client_secret(self) -> bool:
        return CLIENT_SECRET_FILE.exists()

    def get_authorization_url(self) -> Tuple[Optional[str], str]:
        if not self.has_client_secret():
            return None, "client_secret.json not found in credentials folder"

        try:
            self._flow = Flow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE),
                scopes=list(settings.google.scopes),
                redirect_uri=settings.google.redirect_uri,
            )

            auth_url, _ = self._flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )

            return auth_url, "Authorization URL generated"

        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            return None, f"Failed to generate authorization URL: {str(e)}"

    def open_authorization_in_browser(self) -> Tuple[bool, str]:
        auth_url, message = self.get_authorization_url()

        if not auth_url:
            return False, message

        try:
            webbrowser.open(auth_url)
            return True, auth_url
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return False, f"Failed to open browser. Please visit: {auth_url}"

    def authenticate_with_code(self, authorization_code: str) -> Tuple[bool, str]:
        if not self._flow:
            return False, "Authorization flow not initialized. Call get_authorization_url first"

        try:
            self._flow.fetch_token(code=authorization_code)
            credentials = self._flow.credentials

            gmail_service = build("gmail", "v1", credentials=credentials)
            profile = gmail_service.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress")

            if not email:
                return False, "Failed to retrieve email address"

            calendar_service = build("calendar", "v3", credentials=credentials)

            self._session = OAuthSession(
                email=email,
                credentials=credentials,
                gmail_service=gmail_service,
                calendar_service=calendar_service,
                is_authenticated=True,
            )

            self._store_credentials(email, credentials)

            logger.info(f"Successfully authenticated via OAuth: {email}")
            return True, f"Authentication successful for {email}"

        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            return False, f"Authentication failed: {str(e)}"

    def authenticate_from_stored(self) -> Tuple[bool, str]:
        credential = CredentialsRepository.find_first()

        if not credential:
            return False, "No stored credentials found"

        if credential.auth_type != AuthType.OAUTH:
            return False, "Stored credential is not OAuth type"

        try:
            token_data = json.loads(decrypt(credential.encrypted_token))

            credentials = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes"),
            )

            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                self._update_stored_credentials(credential.user_email, credentials)

            gmail_service = build("gmail", "v1", credentials=credentials)
            calendar_service = build("calendar", "v3", credentials=credentials)

            self._session = OAuthSession(
                email=credential.user_email,
                credentials=credentials,
                gmail_service=gmail_service,
                calendar_service=calendar_service,
                is_authenticated=True,
            )

            logger.info(f"Restored OAuth session for: {credential.user_email}")
            return True, f"Session restored for {credential.user_email}"

        except Exception as e:
            logger.error(f"Failed to restore OAuth session: {e}")
            return False, f"Failed to restore session: {str(e)}"

    def refresh_token_if_needed(self) -> bool:
        if not self._session or not self._session.credentials:
            return False

        try:
            if self._session.credentials.expired:
                self._session.credentials.refresh(Request())
                self._update_stored_credentials(
                    self._session.email,
                    self._session.credentials,
                )

                self._session.gmail_service = build(
                    "gmail", "v1",
                    credentials=self._session.credentials,
                )
                self._session.calendar_service = build(
                    "calendar", "v3",
                    credentials=self._session.credentials,
                )

            return True

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False

    def get_gmail_service(self) -> Optional[Resource]:
        if not self._session or not self._session.is_authenticated:
            return None

        self.refresh_token_if_needed()
        return self._session.gmail_service

    def get_calendar_service(self) -> Optional[Resource]:
        if not self._session or not self._session.is_authenticated:
            return None

        self.refresh_token_if_needed()
        return self._session.calendar_service

    def _store_credentials(self, email: str, credentials: Credentials) -> None:
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else [],
        }

        encrypted_token = encrypt(json.dumps(token_data))

        token_expiry = None
        if credentials.expiry:
            token_expiry = credentials.expiry

        credential = Credential(
            user_email=email,
            auth_type=AuthType.OAUTH,
            encrypted_token=encrypted_token,
            access_token=encrypt(credentials.token) if credentials.token else None,
            token_expiry=token_expiry,
        )

        CredentialsRepository.upsert(credential)
        logger.info(f"OAuth credentials stored for: {email}")

    def _update_stored_credentials(self, email: str, credentials: Credentials) -> None:
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else [],
        }

        encrypted_token = encrypt(json.dumps(token_data))

        token_expiry = None
        if credentials.expiry:
            token_expiry = credentials.expiry

        CredentialsRepository.update_tokens(
            user_email=email,
            encrypted_token=encrypted_token,
            access_token=encrypt(credentials.token) if credentials.token else None,
            token_expiry=token_expiry,
        )

    def logout(self) -> None:
        if self._session:
            self._session = None
            self._flow = None
            logger.info("OAuth session ended")

    def delete_stored_credentials(self, email: str) -> bool:
        return CredentialsRepository.delete_by_email(email)

    def verify_connection(self) -> bool:
        if not self._session or not self._session.is_authenticated:
            return False

        try:
            service = self.get_gmail_service()
            if service:
                service.users().getProfile(userId="me").execute()
                return True
            return False
        except Exception:
            return False
