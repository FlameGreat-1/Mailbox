import logging
from typing import Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from src.database.models import Email
from src.database.repositories import EmailsRepository
from src.services.email.client import EmailClient, get_email_client

logger = logging.getLogger(__name__)


@dataclass
class EmailSyncResult:
    success: bool = False
    total_fetched: int = 0
    new_emails: int = 0
    updated_emails: int = 0
    errors: List[str] = field(default_factory=list)
    sync_time: Optional[datetime] = None


class EmailSyncHandler:
    def __init__(self, email_client: Optional[EmailClient] = None):
        self._email_client = email_client or get_email_client()
        self._last_sync: Optional[datetime] = None

    @property
    def last_sync(self) -> Optional[datetime]:
        return self._last_sync

    @property
    def current_email(self) -> Optional[str]:
        return self._email_client.current_email

    def sync_inbox(
        self,
        limit: int = 50,
        full_sync: bool = False,
    ) -> EmailSyncResult:
        return self._sync_folder("inbox", limit, full_sync)

    def sync_sent(self, limit: int = 50) -> EmailSyncResult:
        return self._sync_folder("sent", limit, False)

    def sync_all_folders(self, limit_per_folder: int = 50) -> EmailSyncResult:
        folders = ["inbox", "sent"]
        combined_result = EmailSyncResult(success=True, sync_time=datetime.now())

        for folder in folders:
            result = self._sync_folder(folder, limit_per_folder, False)

            combined_result.total_fetched += result.total_fetched
            combined_result.new_emails += result.new_emails
            combined_result.updated_emails += result.updated_emails
            combined_result.errors.extend(result.errors)

            if not result.success:
                combined_result.success = False

        self._last_sync = datetime.now()
        return combined_result

    def _sync_folder(
        self,
        folder: str,
        limit: int,
        full_sync: bool,
    ) -> EmailSyncResult:
        result = EmailSyncResult(sync_time=datetime.now())

        if not self._email_client.is_authenticated:
            result.errors.append("Not authenticated")
            return result

        try:
            if full_sync:
                emails = self._email_client.fetch_emails(
                    folder=folder,
                    limit=limit,
                    sync_to_db=True,
                )
            else:
                emails = self._email_client.fetch_email_headers(
                    folder=folder,
                    limit=limit,
                    sync_to_db=True,
                )

            result.total_fetched = len(emails)
            result.success = True

            new_count = 0
            for email in emails:
                if not EmailsRepository.message_exists(self.current_email, email.message_id):
                    new_count += 1

            result.new_emails = new_count
            result.updated_emails = result.total_fetched - new_count

            self._last_sync = datetime.now()

            logger.info(
                f"Synced {folder}: {result.total_fetched} emails "
                f"({result.new_emails} new, {result.updated_emails} updated)"
            )

        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"Failed to sync {folder}: {e}")

        return result

    def sync_single_email(self, message_id: str) -> Tuple[bool, Optional[Email]]:
        if not self._email_client.is_authenticated:
            return False, None

        try:
            email = self._email_client.get_email(message_id, from_db=False)
            if email:
                return True, email
            return False, None

        except Exception as e:
            logger.error(f"Failed to sync email {message_id}: {e}")
            return False, None

    def get_sync_status(self) -> dict:
        if not self.current_email:
            return {
                "authenticated": False,
                "last_sync": None,
                "inbox_count": 0,
                "unread_count": 0,
            }

        return {
            "authenticated": self._email_client.is_authenticated,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "inbox_count": EmailsRepository.get_total_count(self.current_email, "inbox"),
            "unread_count": EmailsRepository.get_unread_count(self.current_email, "inbox"),
        }

    def needs_sync(self, max_age_minutes: int = 5) -> bool:
        if not self._last_sync:
            return True

        age = datetime.now() - self._last_sync
        return age.total_seconds() > (max_age_minutes * 60)

    def clear_local_data(self) -> int:
        if not self.current_email:
            return 0

        deleted = EmailsRepository.delete_by_user(self.current_email)
        logger.info(f"Cleared {deleted} emails for {self.current_email}")
        return deleted
