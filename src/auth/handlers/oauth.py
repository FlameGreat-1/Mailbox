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
from src.auth.oauth_callback import OAuthCallbackServer
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

    def authenticate(self) -> Tuple[bool, str]:
        """
        Automatic OAuth authentication with callback server.
        Opens browser, waits for user authorization, captures code automatically.
        """
        if not self.has_client_secret():
            return False, "client_secret.json not found in credentials folder"

        try:
            
            # Prepare OAuth scopes
            scopes = list(settings.google.scopes)
            
            openid_scopes = [
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
            
            for scope in openid_scopes:
                if scope not in scopes:
                    scopes.append(scope)
            
            # Create OAuth flow
            self._flow = Flow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE),
                scopes=scopes,
                redirect_uri=settings.google.redirect_uri,
            )

            # Generate authorization URL
            auth_url, state = self._flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )

            # Start callback server
            callback_server = OAuthCallbackServer(
                port=settings.google.callback_port,
                state=state
            )
            
            logger.info("Starting OAuth callback server...")
            callback_server.start()

            # Open browser for user authorization
            logger.info("Opening browser for Google sign-in...")
            try:
                webbrowser.open(auth_url)
            except Exception as e:
                callback_server.stop()
                logger.error(f"Failed to open browser: {e}")
                return False, f"Failed to open browser. Please visit manually: {auth_url}"

            # Wait for authorization code (blocks until user authorizes or timeout)
            logger.info("Waiting for user authorization...")
            authorization_code = callback_server.wait_for_code(timeout=300)  # 5 minutes timeout
            
            callback_server.stop()

            if not authorization_code:
                return False, "Authorization timeout or cancelled by user"

            # Exchange authorization code for credentials
            logger.info("Exchanging authorization code for credentials...")
            self._flow.fetch_token(code=authorization_code)
            credentials = self._flow.credentials

            # Get user email from Gmail API
            gmail_service = build("gmail", "v1", credentials=credentials)
            profile = gmail_service.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress")

            if not email:
                return False, "Failed to retrieve email address"

            # Build calendar service
            calendar_service = build("calendar", "v3", credentials=credentials)

            # Create session
            self._session = OAuthSession(
                email=email,
                credentials=credentials,
                gmail_service=gmail_service,
                calendar_service=calendar_service,
                is_authenticated=True,
            )

            # Store credentials in database
            self._store_credentials(email, credentials)

            logger.info(f"Successfully authenticated via OAuth: {email}")
            return True, f"Authentication successful for {email}"

        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            return False, f"Authentication failed: {str(e)}"

    def authenticate_from_stored(self, email: str) -> Tuple[bool, str]:
        credential = CredentialsRepository.find_by_email(email)

        if not credential:
            return False, f"No stored credentials found for {email}"

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
