import logging
import time
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path

from src.auth.manager import AuthManager, AuthMethod, get_auth_manager
from src.database.models import Email
from src.database.repositories import EmailsRepository
from src.services.email.providers.imap import IMAPProvider
from src.services.email.providers.smtp import SMTPProvider
from src.services.email.providers.gmail_api import GmailAPIProvider
from src.services.email.parser import EmailParser

logger = logging.getLogger(__name__)


class EmailClient:
    MAX_RETRIES = 3
    BASE_DELAY = 1

    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self._auth_manager = auth_manager or get_auth_manager()
        self._imap_provider: Optional[IMAPProvider] = None
        self._smtp_provider: Optional[SMTPProvider] = None
        self._gmail_provider: Optional[GmailAPIProvider] = None

    @property
    def current_email(self) -> Optional[str]:
        return self._auth_manager.current_email

    @property
    def is_authenticated(self) -> bool:
        return self._auth_manager.is_authenticated

    def _reset_providers(self) -> None:
        self._imap_provider = None
        self._smtp_provider = None
        self._gmail_provider = None

    def _get_delay(self, attempt: int) -> float:
        return self.BASE_DELAY * (2 ** attempt)

    def _get_imap_provider(self) -> Optional[IMAPProvider]:
        if self._auth_manager.active_method not in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
            return None

        connection = self._auth_manager.get_imap_connection()
        if connection:
            use_gmail_folders = self._auth_manager.active_method == AuthMethod.APP_PASSWORD
            self._imap_provider = IMAPProvider(connection, use_gmail_folders=use_gmail_folders)
            return self._imap_provider

        return None

    def _get_smtp_provider(self) -> Optional[SMTPProvider]:
        if self._auth_manager.active_method not in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
            return None

        connection = self._auth_manager.get_smtp_connection()
        if connection:
            self._smtp_provider = SMTPProvider(connection)
            return self._smtp_provider

        return None

    def _get_gmail_provider(self) -> Optional[GmailAPIProvider]:
        if self._auth_manager.active_method != AuthMethod.OAUTH:
            return None

        service = self._auth_manager.get_gmail_service()
        if service:
            self._gmail_provider = GmailAPIProvider(service)
            return self._gmail_provider

        return None

    def fetch_emails(
        self,
        folder: str = "inbox",
        limit: int = 50,
        sync_to_db: bool = True,
    ) -> List[Email]:
        if not self.is_authenticated:
            logger.error("Not authenticated")
            return []

        emails = []

        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        label_map = {
                            "inbox": ["INBOX"],
                            "sent": ["SENT"],
                            "drafts": ["DRAFT"],
                            "spam": ["SPAM"],
                            "trash": ["TRASH"],
                        }
                        labels = label_map.get(folder.lower(), ["INBOX"])
                        emails = provider.fetch_messages(
                            user_email=self.current_email,
                            max_results=limit,
                            label_ids=labels,
                            include_body=True,
                        )

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._imap_provider = None
                    provider = self._get_imap_provider()
                    if provider:
                        emails = provider.fetch_messages(
                            user_email=self.current_email,
                            folder=folder,
                            limit=limit,
                            headers_only=False,
                        )

                if sync_to_db and emails:
                    self._sync_emails_to_db(emails)

                return emails

            except Exception as e:
                logger.warning(f"Fetch emails attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Fetch emails failed after {self.MAX_RETRIES} attempts: {e}")
                    return []

        return []

    def fetch_email_headers(
        self,
        folder: str = "inbox",
        limit: int = 50,
        sync_to_db: bool = True,
    ) -> List[Email]:
        if not self.is_authenticated:
            logger.error("Not authenticated")
            return []

        emails = []

        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        label_map = {
                            "inbox": ["INBOX"],
                            "sent": ["SENT"],
                            "drafts": ["DRAFT"],
                            "spam": ["SPAM"],
                            "trash": ["TRASH"],
                        }
                        labels = label_map.get(folder.lower(), ["INBOX"])
                        emails = provider.fetch_messages(
                            user_email=self.current_email,
                            max_results=limit,
                            label_ids=labels,
                            include_body=False,
                        )

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._imap_provider = None
                    provider = self._get_imap_provider()
                    if provider:
                        emails = provider.fetch_messages(
                            user_email=self.current_email,
                            folder=folder,
                            limit=limit,
                            headers_only=True,
                        )

                if sync_to_db and emails:
                    self._sync_emails_to_db(emails)

                return emails

            except Exception as e:
                logger.warning(f"Fetch email headers attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Fetch email headers failed after {self.MAX_RETRIES} attempts: {e}")
                    return []

        return []

    def get_email(self, message_id: str, from_db: bool = True) -> Optional[Email]:
        if from_db:
            email_obj = EmailsRepository.find_by_message_id(self.current_email, message_id)
            if email_obj and email_obj.body_text:
                return email_obj

        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        email_obj = provider.fetch_message(message_id, self.current_email, include_body=True)
                        if email_obj:
                            self._sync_emails_to_db([email_obj])
                        return email_obj

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._imap_provider = None
                    provider = self._get_imap_provider()
                    if provider:
                        email_obj = provider.fetch_message(message_id, self.current_email)
                        if email_obj:
                            self._sync_emails_to_db([email_obj])
                        return email_obj

                return None

            except Exception as e:
                logger.warning(f"Get email attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    raise

        return None

    def get_emails_from_db(
        self,
        folder: str = "inbox",
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> List[Email]:
        if not self.current_email:
            return []

        return EmailsRepository.find_by_user(
            user_email=self.current_email,
            folder=folder,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )

    def search_emails(self, query: str, limit: int = 50) -> List[Email]:
        if not self.is_authenticated:
            return []

        db_results = EmailsRepository.search(self.current_email, query, limit)

        if db_results:
            return db_results

        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        return provider.search_messages(self.current_email, query, limit)

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._imap_provider = None
                    provider = self._get_imap_provider()
                    if provider:
                        return provider.search_messages(self.current_email, query, limit=limit)

                return []

            except Exception as e:
                logger.warning(f"Search emails attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Search emails failed after {self.MAX_RETRIES} attempts: {e}")
                    return []

        return []

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        if not self.is_authenticated:
            return False, "Not authenticated"

        to_emails = EmailParser.validate_email_list(to_emails)
        if not to_emails:
            return False, "No valid recipient email addresses"

        if cc_emails:
            cc_emails = EmailParser.validate_email_list(cc_emails)

        if bcc_emails:
            bcc_emails = EmailParser.validate_email_list(bcc_emails)

        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        return provider.send_email(
                            from_email=self.current_email,
                            to_emails=to_emails,
                            subject=subject,
                            body_text=body_text,
                            body_html=body_html,
                            cc_emails=cc_emails,
                            bcc_emails=bcc_emails,
                            attachments=attachments,
                        )

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._smtp_provider = None
                    provider = self._get_smtp_provider()
                    if provider:
                        return provider.send_email(
                            from_email=self.current_email,
                            to_emails=to_emails,
                            subject=subject,
                            body_text=body_text,
                            body_html=body_html,
                            cc_emails=cc_emails,
                            bcc_emails=bcc_emails,
                            attachments=attachments,
                        )

                return False, "No email provider available"

            except Exception as e:
                logger.warning(f"Send email attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    return False, f"Failed to send email: {str(e)}"

        return False, "Failed to send email after retries"

    def send_reply(
        self,
        original_email: Email,
        body_text: str,
        body_html: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        include_original: bool = True,
    ) -> Tuple[bool, str]:
        if not self.is_authenticated:
            return False, "Not authenticated"

        reply_to = EmailParser.extract_reply_address(original_email)

        if include_original:
            body_text = body_text + EmailParser.create_reply_body(original_email)

        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        return provider.send_reply(
                            from_email=self.current_email,
                            to_email=reply_to,
                            subject=original_email.subject,
                            body_text=body_text,
                            original_message_id=original_email.message_id,
                            thread_id=original_email.thread_id or original_email.message_id,
                            body_html=body_html,
                            cc_emails=cc_emails,
                        )

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._smtp_provider = None
                    provider = self._get_smtp_provider()
                    if provider:
                        return provider.send_reply(
                            from_email=self.current_email,
                            to_email=reply_to,
                            subject=original_email.subject,
                            body_text=body_text,
                            original_message_id=original_email.thread_id or original_email.message_id,
                            body_html=body_html,
                            cc_emails=cc_emails,
                        )

                return False, "No email provider available"

            except Exception as e:
                logger.warning(f"Send reply attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    return False, f"Failed to send reply: {str(e)}"

        return False, "Failed to send reply after retries"

    def mark_as_read(self, message_id: str) -> bool:
        email_obj = EmailsRepository.find_by_message_id(self.current_email, message_id)
        if email_obj:
            EmailsRepository.mark_as_read(email_obj.id)

        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        return provider.mark_as_read(message_id)

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._imap_provider = None
                    provider = self._get_imap_provider()
                    if provider:
                        return provider.mark_as_read(message_id)

                return False

            except Exception as e:
                logger.warning(f"Mark as read attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Mark as read failed after {self.MAX_RETRIES} attempts: {e}")
                    return False

        return False

    def mark_as_unread(self, message_id: str) -> bool:
        email_obj = EmailsRepository.find_by_message_id(self.current_email, message_id)
        if email_obj:
            EmailsRepository.mark_as_unread(email_obj.id)

        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        return provider.mark_as_unread(message_id)

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._imap_provider = None
                    provider = self._get_imap_provider()
                    if provider:
                        return provider.mark_as_unread(message_id)

                return False

            except Exception as e:
                logger.warning(f"Mark as unread attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Mark as unread failed after {self.MAX_RETRIES} attempts: {e}")
                    return False

        return False

    def save_attachment(
        self,
        message_id: str,
        attachment_index: int,
        save_path: str,
    ) -> Tuple[bool, str]:
        for attempt in range(self.MAX_RETRIES):
            try:
                if self._auth_manager.active_method == AuthMethod.OAUTH:
                    email_obj = self.get_email(message_id)
                    if not email_obj:
                        return False, "Email not found"

                    attachments = EmailParser.parse_attachments_meta(email_obj.attachments_meta)
                    if attachment_index >= len(attachments):
                        return False, "Attachment not found"

                    attachment_meta = attachments[attachment_index]
                    attachment_id = attachment_meta.get("attachment_id")

                    if not attachment_id:
                        return False, "Attachment ID not found"

                    self._gmail_provider = None
                    provider = self._get_gmail_provider()
                    if provider:
                        attachment_data = provider.get_attachment(message_id, attachment_id)
                        if attachment_data:
                            save_file = Path(save_path) / attachment_meta["filename"]
                            save_file.write_bytes(attachment_data["data"])
                            return True, f"Saved to {save_file}"

                elif self._auth_manager.active_method in [AuthMethod.APP_PASSWORD, AuthMethod.ZOHO]:
                    self._imap_provider = None
                    provider = self._get_imap_provider()
                    if provider:
                        attachment = provider.get_attachment(message_id, attachment_index)
                        if attachment:
                            save_file = Path(save_path) / attachment["filename"]
                            save_file.write_bytes(attachment["data"])
                            return True, f"Saved to {save_file}"

                return False, "Failed to retrieve attachment"

            except Exception as e:
                logger.warning(f"Save attachment attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_providers()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    return False, f"Failed to save attachment: {str(e)}"

        return False, "Failed to save attachment after retries"

    def get_unread_count(self, folder: str = "inbox") -> int:
        if not self.current_email:
            return 0

        return EmailsRepository.get_unread_count(self.current_email, folder)

    def get_total_count(self, folder: str = "inbox") -> int:
        if not self.current_email:
            return 0

        return EmailsRepository.get_total_count(self.current_email, folder)

    def _sync_emails_to_db(self, emails: List[Email]) -> int:
        if not emails:
            return 0

        return EmailsRepository.bulk_insert(emails)


_email_client = None


def get_email_client() -> EmailClient:
    global _email_client
    if _email_client is None:
        _email_client = EmailClient()
    return _email_client
