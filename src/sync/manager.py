import logging
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field
from threading import Lock

from src.auth.manager import AuthManager, get_auth_manager
from src.sync.handlers.email import EmailSyncHandler, EmailSyncResult
from src.sync.handlers.calendar import CalendarSyncHandler, CalendarSyncResult

logger = logging.getLogger(__name__)


@dataclass
class FullSyncResult:
    success: bool = False
    email_result: Optional[EmailSyncResult] = None
    calendar_result: Optional[CalendarSyncResult] = None
    sync_time: Optional[datetime] = None
    errors: list = field(default_factory=list)


class SyncManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SyncManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._auth_manager = get_auth_manager()
        self._email_handler = EmailSyncHandler()
        self._calendar_handler = CalendarSyncHandler()
        self._last_full_sync: Optional[datetime] = None
        self._sync_in_progress = False
        self._initialized = True

    @property
    def email_handler(self) -> EmailSyncHandler:
        return self._email_handler

    @property
    def calendar_handler(self) -> CalendarSyncHandler:
        return self._calendar_handler

    @property
    def last_full_sync(self) -> Optional[datetime]:
        return self._last_full_sync

    @property
    def is_syncing(self) -> bool:
        return self._sync_in_progress

    def sync_all(
        self,
        email_limit: int = 50,
        calendar_days: int = 7,
    ) -> FullSyncResult:
        if self._sync_in_progress:
            return FullSyncResult(
                success=False,
                errors=["Sync already in progress"],
            )

        self._sync_in_progress = True
        result = FullSyncResult(sync_time=datetime.now())

        try:
            result.email_result = self._email_handler.sync_inbox(limit=email_limit)

            if self._calendar_handler.is_available():
                result.calendar_result = self._calendar_handler.sync_upcoming(
                    days_ahead=calendar_days,
                )

            result.success = True

            if result.email_result and not result.email_result.success:
                result.success = False
                result.errors.extend(result.email_result.errors)

            if result.calendar_result and not result.calendar_result.success:
                result.errors.extend(result.calendar_result.errors)

            self._last_full_sync = datetime.now()

            logger.info("Full sync completed successfully")

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Full sync failed: {e}")

        finally:
            self._sync_in_progress = False

        return result

    def sync_emails(self, limit: int = 50, full_sync: bool = False) -> EmailSyncResult:
        if self._sync_in_progress:
            return EmailSyncResult(
                success=False,
                errors=["Sync already in progress"],
            )

        self._sync_in_progress = True

        try:
            return self._email_handler.sync_inbox(limit=limit, full_sync=full_sync)
        finally:
            self._sync_in_progress = False

    def sync_calendar(self, days_ahead: int = 7) -> CalendarSyncResult:
        if self._sync_in_progress:
            return CalendarSyncResult(
                success=False,
                errors=["Sync already in progress"],
            )

        if not self._calendar_handler.is_available():
            return CalendarSyncResult(
                success=False,
                errors=["Calendar not available (requires OAuth authentication)"],
            )

        self._sync_in_progress = True

        try:
            return self._calendar_handler.sync_upcoming(days_ahead=days_ahead)
        finally:
            self._sync_in_progress = False

    def sync_if_needed(
        self,
        email_max_age_minutes: int = 5,
        calendar_max_age_minutes: int = 15,
    ) -> FullSyncResult:
        result = FullSyncResult(sync_time=datetime.now())

        if self._email_handler.needs_sync(email_max_age_minutes):
            result.email_result = self.sync_emails()

        if (
            self._calendar_handler.is_available()
            and self._calendar_handler.needs_sync(calendar_max_age_minutes)
        ):
            result.calendar_result = self.sync_calendar()

        result.success = True

        if result.email_result and not result.email_result.success:
            result.success = False
            result.errors.extend(result.email_result.errors)

        if result.calendar_result and not result.calendar_result.success:
            result.errors.extend(result.calendar_result.errors)

        return result

    def get_sync_status(self) -> dict:
        return {
            "syncing": self._sync_in_progress,
            "last_full_sync": self._last_full_sync.isoformat() if self._last_full_sync else None,
            "email": self._email_handler.get_sync_status(),
            "calendar": self._calendar_handler.get_sync_status(),
        }

    def clear_all_local_data(self) -> dict:
        emails_deleted = self._email_handler.clear_local_data()
        events_deleted = self._calendar_handler.clear_local_data()

        return {
            "emails_deleted": emails_deleted,
            "events_deleted": events_deleted,
        }

    def initial_sync(self) -> FullSyncResult:
        return self.sync_all(email_limit=100, calendar_days=30)


_sync_manager = None


def get_sync_manager() -> SyncManager:
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
    return _sync_manager
