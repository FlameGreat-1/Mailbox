import logging
import time
from typing import Optional, List
from datetime import datetime, timedelta

from src.auth.manager import AuthManager, AuthMethod, get_auth_manager
from src.database.models import CalendarEvent
from src.database.repositories import CalendarRepository
from src.services.calendar.providers.google_api import GoogleCalendarProvider

logger = logging.getLogger(__name__)


class CalendarClient:
    MAX_RETRIES = 3
    BASE_DELAY = 1

    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self._auth_manager = auth_manager or get_auth_manager()
        self._google_provider: Optional[GoogleCalendarProvider] = None

    @property
    def current_email(self) -> Optional[str]:
        return self._auth_manager.current_email

    @property
    def is_authenticated(self) -> bool:
        return self._auth_manager.is_authenticated

    def _reset_provider(self) -> None:
        self._google_provider = None

    def _get_delay(self, attempt: int) -> float:
        return self.BASE_DELAY * (2 ** attempt)

    def _get_google_provider(self) -> Optional[GoogleCalendarProvider]:
        if self._auth_manager.active_method != AuthMethod.OAUTH:
            return None

        service = self._auth_manager.get_calendar_service()
        if service:
            self._google_provider = GoogleCalendarProvider(service)
            return self._google_provider

        return None

    def is_calendar_available(self) -> bool:
        return self._auth_manager.active_method == AuthMethod.OAUTH

    def fetch_events(
        self,
        days_ahead: int = 7,
        max_results: int = 50,
        sync_to_db: bool = True,
    ) -> List[CalendarEvent]:
        if not self.is_authenticated:
            logger.error("Not authenticated")
            return []

        if not self.is_calendar_available():
            logger.warning("Calendar not available with App Password authentication")
            return []

        for attempt in range(self.MAX_RETRIES):
            try:
                self._reset_provider()
                provider = self._get_google_provider()
                if not provider:
                    return []

                events = provider.fetch_upcoming_events(
                    user_email=self.current_email,
                    days_ahead=days_ahead,
                    max_results=max_results,
                )

                if sync_to_db and events:
                    self._sync_events_to_db(events)

                return events

            except Exception as e:
                logger.warning(f"Fetch events attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_provider()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Fetch events failed after {self.MAX_RETRIES} attempts: {e}")
                    return []

        return []

    def fetch_today_events(self, sync_to_db: bool = True) -> List[CalendarEvent]:
        if not self.is_authenticated or not self.is_calendar_available():
            return []

        for attempt in range(self.MAX_RETRIES):
            try:
                self._reset_provider()
                provider = self._get_google_provider()
                if not provider:
                    return []

                events = provider.fetch_today_events(self.current_email)

                if sync_to_db and events:
                    self._sync_events_to_db(events)

                return events

            except Exception as e:
                logger.warning(f"Fetch today events attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_provider()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Fetch today events failed after {self.MAX_RETRIES} attempts: {e}")
                    return []

        return []

    def fetch_events_by_range(
        self,
        start_date: datetime,
        end_date: datetime,
        sync_to_db: bool = True,
    ) -> List[CalendarEvent]:
        if not self.is_authenticated or not self.is_calendar_available():
            return []

        for attempt in range(self.MAX_RETRIES):
            try:
                self._reset_provider()
                provider = self._get_google_provider()
                if not provider:
                    return []

                events = provider.fetch_events(
                    user_email=self.current_email,
                    time_min=start_date,
                    time_max=end_date,
                )

                if sync_to_db and events:
                    self._sync_events_to_db(events)

                return events

            except Exception as e:
                logger.warning(f"Fetch events by range attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_provider()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Fetch events by range failed after {self.MAX_RETRIES} attempts: {e}")
                    return []

        return []

    def get_event(self, event_id: str, from_db: bool = True) -> Optional[CalendarEvent]:
        if from_db:
            event = CalendarRepository.find_by_event_id(self.current_email, event_id)
            if event:
                return event

        if not self.is_calendar_available():
            return None

        for attempt in range(self.MAX_RETRIES):
            try:
                self._reset_provider()
                provider = self._get_google_provider()
                if provider:
                    event = provider.fetch_event(event_id, self.current_email)
                    if event:
                        self._sync_events_to_db([event])
                    return event

                return None

            except Exception as e:
                logger.warning(f"Get event attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_provider()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Get event failed after {self.MAX_RETRIES} attempts: {e}")
                    return None

        return None

    def get_events_from_db(
        self,
        days_ahead: int = 7,
        limit: int = 50,
    ) -> List[CalendarEvent]:
        if not self.current_email:
            return []

        return CalendarRepository.find_upcoming(
            user_email=self.current_email,
            days_ahead=days_ahead,
            limit=limit,
        )

    def get_today_events_from_db(self) -> List[CalendarEvent]:
        if not self.current_email:
            return []

        return CalendarRepository.find_today(self.current_email)

    def get_events_by_range_from_db(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        if not self.current_email:
            return []

        return CalendarRepository.find_by_date_range(
            user_email=self.current_email,
            start_date=start_date,
            end_date=end_date,
        )

    def search_events(self, query: str, max_results: int = 50) -> List[CalendarEvent]:
        if not self.is_authenticated or not self.is_calendar_available():
            return []

        for attempt in range(self.MAX_RETRIES):
            try:
                self._reset_provider()
                provider = self._get_google_provider()
                if provider:
                    return provider.search_events(
                        user_email=self.current_email,
                        query=query,
                        max_results=max_results,
                    )

                return []

            except Exception as e:
                logger.warning(f"Search events attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_provider()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Search events failed after {self.MAX_RETRIES} attempts: {e}")
                    return []

        return []

    def get_calendars(self) -> List[dict]:
        if not self.is_authenticated or not self.is_calendar_available():
            return []

        for attempt in range(self.MAX_RETRIES):
            try:
                self._reset_provider()
                provider = self._get_google_provider()
                if provider:
                    return provider.get_calendars()

                return []

            except Exception as e:
                logger.warning(f"Get calendars attempt {attempt + 1} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    self._reset_provider()
                    time.sleep(self._get_delay(attempt))
                    continue
                else:
                    logger.error(f"Get calendars failed after {self.MAX_RETRIES} attempts: {e}")
                    return []

        return []

    def get_event_count(self, days_ahead: int = 7) -> int:
        if not self.current_email:
            return 0

        return CalendarRepository.get_event_count(self.current_email, days_ahead)

    def sync_calendar(self, days_ahead: int = 30) -> int:
        if not self.is_authenticated or not self.is_calendar_available():
            return 0

        events = self.fetch_events(days_ahead=days_ahead, max_results=250, sync_to_db=True)
        return len(events)

    def cleanup_old_events(self, days_old: int = 30) -> int:
        if not self.current_email:
            return 0

        return CalendarRepository.delete_past_events(self.current_email, days_old)

    def _sync_events_to_db(self, events: List[CalendarEvent]) -> int:
        if not events:
            return 0

        return CalendarRepository.bulk_upsert(events)

    @staticmethod
    def format_event_time(event: CalendarEvent) -> str:
        if not event.start_time:
            return ""

        if event.is_all_day:
            return event.start_time.strftime("%b %d, %Y") + " (All Day)"

        start_str = event.start_time.strftime("%b %d, %Y %I:%M %p")

        if event.end_time:
            if event.start_time.date() == event.end_time.date():
                end_str = event.end_time.strftime("%I:%M %p")
            else:
                end_str = event.end_time.strftime("%b %d, %Y %I:%M %p")
            return f"{start_str} - {end_str}"

        return start_str

    @staticmethod
    def format_event_time_short(event: CalendarEvent) -> str:
        if not event.start_time:
            return ""

        if event.is_all_day:
            return "All Day"

        start_str = event.start_time.strftime("%I:%M %p")

        if event.end_time:
            end_str = event.end_time.strftime("%I:%M %p")
            return f"{start_str} - {end_str}"

        return start_str

    @staticmethod
    def format_event_date(event: CalendarEvent) -> str:
        if not event.start_time:
            return ""

        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        event_date = event.start_time.date()

        if event_date == today:
            return "Today"
        elif event_date == tomorrow:
            return "Tomorrow"
        else:
            return event.start_time.strftime("%A, %b %d")

    @staticmethod
    def get_event_duration_minutes(event: CalendarEvent) -> int:
        if not event.start_time or not event.end_time:
            return 0

        if event.is_all_day:
            return 24 * 60

        delta = event.end_time - event.start_time
        return int(delta.total_seconds() / 60)


_calendar_client = None


def get_calendar_client() -> CalendarClient:
    global _calendar_client
    if _calendar_client is None:
        _calendar_client = CalendarClient()
    return _calendar_client
