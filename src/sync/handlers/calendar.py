import logging
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from src.database.models import CalendarEvent
from src.database.repositories import CalendarRepository
from src.services.calendar.client import CalendarClient, get_calendar_client

logger = logging.getLogger(__name__)


@dataclass
class CalendarSyncResult:
    success: bool = False
    total_fetched: int = 0
    new_events: int = 0
    updated_events: int = 0
    errors: List[str] = field(default_factory=list)
    sync_time: Optional[datetime] = None


class CalendarSyncHandler:
    def __init__(self, calendar_client: Optional[CalendarClient] = None):
        self._calendar_client = calendar_client or get_calendar_client()
        self._last_sync: Optional[datetime] = None

    @property
    def last_sync(self) -> Optional[datetime]:
        return self._last_sync

    @property
    def current_email(self) -> Optional[str]:
        return self._calendar_client.current_email

    def is_available(self) -> bool:
        return self._calendar_client.is_calendar_available()

    def sync_upcoming(
        self,
        days_ahead: int = 7,
        max_results: int = 50,
    ) -> CalendarSyncResult:
        result = CalendarSyncResult(sync_time=datetime.now())

        if not self._calendar_client.is_authenticated:
            result.errors.append("Not authenticated")
            return result

        if not self.is_available():
            result.errors.append("Calendar not available (requires OAuth authentication)")
            return result

        try:
            existing_count = CalendarRepository.get_event_count(self.current_email, days_ahead)

            events = self._calendar_client.fetch_events(
                days_ahead=days_ahead,
                max_results=max_results,
                sync_to_db=True,
            )

            result.total_fetched = len(events)
            result.success = True

            new_count = 0
            for event in events:
                if not CalendarRepository.event_exists(self.current_email, event.event_id):
                    new_count += 1

            result.new_events = new_count
            result.updated_events = result.total_fetched - new_count

            self._last_sync = datetime.now()

            logger.info(
                f"Synced calendar: {result.total_fetched} events "
                f"({result.new_events} new, {result.updated_events} updated)"
            )

        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"Failed to sync calendar: {e}")

        return result

    def sync_today(self) -> CalendarSyncResult:
        result = CalendarSyncResult(sync_time=datetime.now())

        if not self._calendar_client.is_authenticated:
            result.errors.append("Not authenticated")
            return result

        if not self.is_available():
            result.errors.append("Calendar not available (requires OAuth authentication)")
            return result

        try:
            events = self._calendar_client.fetch_today_events(sync_to_db=True)

            result.total_fetched = len(events)
            result.success = True
            result.new_events = len(events)

            self._last_sync = datetime.now()

            logger.info(f"Synced today's events: {result.total_fetched} events")

        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"Failed to sync today's events: {e}")

        return result

    def sync_month(self) -> CalendarSyncResult:
        return self.sync_upcoming(days_ahead=30, max_results=100)

    def get_sync_status(self) -> dict:
        if not self.current_email:
            return {
                "authenticated": False,
                "available": False,
                "last_sync": None,
                "upcoming_count": 0,
                "today_count": 0,
            }

        today_events = CalendarRepository.find_today(self.current_email)

        return {
            "authenticated": self._calendar_client.is_authenticated,
            "available": self.is_available(),
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "upcoming_count": CalendarRepository.get_event_count(self.current_email, 7),
            "today_count": len(today_events),
        }

    def needs_sync(self, max_age_minutes: int = 15) -> bool:
        if not self._last_sync:
            return True

        age = datetime.now() - self._last_sync
        return age.total_seconds() > (max_age_minutes * 60)

    def clear_local_data(self) -> int:
        if not self.current_email:
            return 0

        deleted = CalendarRepository.delete_by_user(self.current_email)
        logger.info(f"Cleared {deleted} calendar events for {self.current_email}")
        return deleted

    def cleanup_old_events(self, days_old: int = 30) -> int:
        if not self.current_email:
            return 0

        deleted = CalendarRepository.delete_past_events(self.current_email, days_old)
        logger.info(f"Cleaned up {deleted} old events for {self.current_email}")
        return deleted
