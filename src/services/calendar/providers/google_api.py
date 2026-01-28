import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from src.database.models import CalendarEvent

logger = logging.getLogger(__name__)


class GoogleCalendarProvider:
    def __init__(self, service: Resource):
        self._service = service

    @property
    def service(self) -> Resource:
        return self._service

    def fetch_events(
        self,
        user_email: str,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
        single_events: bool = True,
    ) -> List[CalendarEvent]:
        try:
            if time_min is None:
                time_min = datetime.now()

            if time_max is None:
                time_max = time_min + timedelta(days=30)

            time_min_str = time_min.isoformat() + "Z" if time_min.tzinfo is None else time_min.isoformat()
            time_max_str = time_max.isoformat() + "Z" if time_max.tzinfo is None else time_max.isoformat()

            response = self._service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_str,
                timeMax=time_max_str,
                maxResults=max_results,
                singleEvents=single_events,
                orderBy="startTime",
            ).execute()

            events = response.get("items", [])

            return [self._parse_event(event, user_email, calendar_id) for event in events]

        except HttpError as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            return []

    def fetch_upcoming_events(
        self,
        user_email: str,
        days_ahead: int = 7,
        max_results: int = 50,
    ) -> List[CalendarEvent]:
        time_min = datetime.now()
        time_max = time_min + timedelta(days=days_ahead)

        return self.fetch_events(
            user_email=user_email,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
        )

    def fetch_today_events(self, user_email: str) -> List[CalendarEvent]:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        return self.fetch_events(
            user_email=user_email,
            time_min=today_start,
            time_max=today_end,
            max_results=100,
        )

    def fetch_event(
        self,
        event_id: str,
        user_email: str,
        calendar_id: str = "primary",
    ) -> Optional[CalendarEvent]:
        try:
            event = self._service.events().get(
                calendarId=calendar_id,
                eventId=event_id,
            ).execute()

            return self._parse_event(event, user_email, calendar_id)

        except HttpError as e:
            logger.error(f"Failed to fetch event {event_id}: {e}")
            return None

    def get_calendars(self) -> List[Dict[str, Any]]:
        try:
            response = self._service.calendarList().list().execute()
            calendars = response.get("items", [])

            return [
                {
                    "id": cal.get("id"),
                    "summary": cal.get("summary"),
                    "description": cal.get("description"),
                    "primary": cal.get("primary", False),
                    "background_color": cal.get("backgroundColor"),
                    "access_role": cal.get("accessRole"),
                }
                for cal in calendars
            ]

        except HttpError as e:
            logger.error(f"Failed to fetch calendars: {e}")
            return []

    def search_events(
        self,
        user_email: str,
        query: str,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[CalendarEvent]:
        try:
            if time_min is None:
                time_min = datetime.now() - timedelta(days=30)

            if time_max is None:
                time_max = datetime.now() + timedelta(days=365)

            time_min_str = time_min.isoformat() + "Z" if time_min.tzinfo is None else time_min.isoformat()
            time_max_str = time_max.isoformat() + "Z" if time_max.tzinfo is None else time_max.isoformat()

            response = self._service.events().list(
                calendarId="primary",
                timeMin=time_min_str,
                timeMax=time_max_str,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
                q=query,
            ).execute()

            events = response.get("items", [])

            return [self._parse_event(event, user_email, "primary") for event in events]

        except HttpError as e:
            logger.error(f"Failed to search events: {e}")
            return []

    def _parse_event(
        self,
        event: Dict[str, Any],
        user_email: str,
        calendar_id: str,
    ) -> CalendarEvent:
        start = event.get("start", {})
        end = event.get("end", {})

        is_all_day = "date" in start

        if is_all_day:
            start_time = self._parse_date(start.get("date"))
            end_time = self._parse_date(end.get("date"))
        else:
            start_time = self._parse_datetime(start.get("dateTime"))
            end_time = self._parse_datetime(end.get("dateTime"))

        attendees = []
        for attendee in event.get("attendees", []):
            email = attendee.get("email")
            if email:
                attendees.append(email)

        meeting_link = None
        conference_data = event.get("conferenceData")
        if conference_data:
            entry_points = conference_data.get("entryPoints", [])
            for entry in entry_points:
                if entry.get("entryPointType") == "video":
                    meeting_link = entry.get("uri")
                    break

        if not meeting_link:
            hangout_link = event.get("hangoutLink")
            if hangout_link:
                meeting_link = hangout_link

        return CalendarEvent(
            user_email=user_email,
            event_id=event.get("id", ""),
            calendar_id=calendar_id,
            title=event.get("summary", "(No Title)"),
            description=event.get("description"),
            location=event.get("location"),
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
            attendees=attendees,
            meeting_link=meeting_link,
            status=event.get("status", "confirmed"),
        )

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None

        try:
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1] + "+00:00"

            from dateutil import parser
            return parser.isoparse(dt_str).replace(tzinfo=None)

        except Exception as e:
            logger.error(f"Failed to parse datetime {dt_str}: {e}")
            return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except Exception as e:
            logger.error(f"Failed to parse date {date_str}: {e}")
            return None
