import json
from typing import Optional, List
from datetime import datetime, timedelta
from src.database.connection import get_cursor, execute_many
from src.database.models import CalendarEvent


class CalendarRepository:
    TABLE_NAME = "calendar_events"

    @classmethod
    def create_table(cls) -> None:
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            event_id VARCHAR(255) NOT NULL,
            calendar_id VARCHAR(255) DEFAULT 'primary',
            title VARCHAR(500) NOT NULL,
            description TEXT,
            location VARCHAR(500),
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            is_all_day BOOLEAN DEFAULT FALSE,
            attendees JSON,
            meeting_link VARCHAR(500),
            status VARCHAR(50) DEFAULT 'confirmed',
            synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_event (user_email, event_id),
            INDEX idx_user_email (user_email),
            INDEX idx_start_time (start_time),
            INDEX idx_end_time (end_time),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with get_cursor() as cursor:
            cursor.execute(query)

    @classmethod
    def save(cls, event: CalendarEvent) -> CalendarEvent:
        if event.id:
            return cls._update(event)
        return cls._insert(event)

    @classmethod
    def _insert(cls, event: CalendarEvent) -> CalendarEvent:
        query = f"""
        INSERT INTO {cls.TABLE_NAME} 
        (user_email, event_id, calendar_id, title, description, location,
         start_time, end_time, is_all_day, attendees, meeting_link, status, synced_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        data = event.to_dict()
        params = (
            data["user_email"],
            data["event_id"],
            data["calendar_id"],
            data["title"],
            data["description"],
            data["location"],
            data["start_time"],
            data["end_time"],
            data["is_all_day"],
            data["attendees"],
            data["meeting_link"],
            data["status"],
            datetime.now(),
        )

        with get_cursor() as cursor:
            cursor.execute(query, params)
            event.id = cursor.lastrowid

        return event

    @classmethod
    def _update(cls, event: CalendarEvent) -> CalendarEvent:
        query = f"""
        UPDATE {cls.TABLE_NAME}
        SET calendar_id = %s, title = %s, description = %s, location = %s,
            start_time = %s, end_time = %s, is_all_day = %s, attendees = %s,
            meeting_link = %s, status = %s, synced_at = %s
        WHERE id = %s
        """
        data = event.to_dict()
        params = (
            data["calendar_id"],
            data["title"],
            data["description"],
            data["location"],
            data["start_time"],
            data["end_time"],
            data["is_all_day"],
            data["attendees"],
            data["meeting_link"],
            data["status"],
            datetime.now(),
            event.id,
        )

        with get_cursor() as cursor:
            cursor.execute(query, params)

        return event

    @classmethod
    def bulk_upsert(cls, events: List[CalendarEvent]) -> int:
        if not events:
            return 0

        query = f"""
        INSERT INTO {cls.TABLE_NAME} 
        (user_email, event_id, calendar_id, title, description, location,
         start_time, end_time, is_all_day, attendees, meeting_link, status, synced_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            calendar_id = VALUES(calendar_id),
            title = VALUES(title),
            description = VALUES(description),
            location = VALUES(location),
            start_time = VALUES(start_time),
            end_time = VALUES(end_time),
            is_all_day = VALUES(is_all_day),
            attendees = VALUES(attendees),
            meeting_link = VALUES(meeting_link),
            status = VALUES(status),
            synced_at = VALUES(synced_at)
        """
        now = datetime.now()
        data = []
        for event in events:
            d = event.to_dict()
            data.append((
                d["user_email"],
                d["event_id"],
                d["calendar_id"],
                d["title"],
                d["description"],
                d["location"],
                d["start_time"],
                d["end_time"],
                d["is_all_day"],
                d["attendees"],
                d["meeting_link"],
                d["status"],
                now,
            ))

        return execute_many(query, data)

    @classmethod
    def find_by_id(cls, event_id: int) -> Optional[CalendarEvent]:
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE id = %s"

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (event_id,))
            row = cursor.fetchone()

            if row:
                return CalendarEvent.from_db_row(row)
            return None

    @classmethod
    def find_by_event_id(cls, user_email: str, event_id: str) -> Optional[CalendarEvent]:
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE user_email = %s AND event_id = %s"

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email, event_id))
            row = cursor.fetchone()

            if row:
                return CalendarEvent.from_db_row(row)
            return None

    @classmethod
    def find_upcoming(
        cls,
        user_email: str,
        days_ahead: int = 7,
        limit: int = 50,
    ) -> List[CalendarEvent]:
        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)

        query = f"""
        SELECT * FROM {cls.TABLE_NAME}
        WHERE user_email = %s 
        AND start_time >= %s 
        AND start_time <= %s
        AND status != 'cancelled'
        ORDER BY start_time ASC
        LIMIT %s
        """

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email, now, end_date, limit))
            rows = cursor.fetchall()

            return [CalendarEvent.from_db_row(row) for row in rows]

    @classmethod
    def find_by_date_range(
        cls,
        user_email: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        query = f"""
        SELECT * FROM {cls.TABLE_NAME}
        WHERE user_email = %s 
        AND start_time >= %s 
        AND start_time <= %s
        AND status != 'cancelled'
        ORDER BY start_time ASC
        """

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email, start_date, end_date))
            rows = cursor.fetchall()

            return [CalendarEvent.from_db_row(row) for row in rows]

    @classmethod
    def find_today(cls, user_email: str) -> List[CalendarEvent]:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        return cls.find_by_date_range(user_email, today_start, today_end)

    @classmethod
    def get_event_count(cls, user_email: str, days_ahead: int = 7) -> int:
        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)

        query = f"""
        SELECT COUNT(*) as count FROM {cls.TABLE_NAME}
        WHERE user_email = %s 
        AND start_time >= %s 
        AND start_time <= %s
        AND status != 'cancelled'
        """

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email, now, end_date))
            row = cursor.fetchone()
            return row["count"] if row else 0

    @classmethod
    def event_exists(cls, user_email: str, event_id: str) -> bool:
        query = f"""
        SELECT 1 FROM {cls.TABLE_NAME}
        WHERE user_email = %s AND event_id = %s LIMIT 1
        """

        with get_cursor() as cursor:
            cursor.execute(query, (user_email, event_id))
            return cursor.fetchone() is not None

    @classmethod
    def delete_by_user(cls, user_email: str) -> int:
        query = f"DELETE FROM {cls.TABLE_NAME} WHERE user_email = %s"

        with get_cursor() as cursor:
            cursor.execute(query, (user_email,))
            return cursor.rowcount

    @classmethod
    def delete_past_events(cls, user_email: str, days_old: int = 30) -> int:
        cutoff_date = datetime.now() - timedelta(days=days_old)

        query = f"""
        DELETE FROM {cls.TABLE_NAME}
        WHERE user_email = %s AND end_time < %s
        """

        with get_cursor() as cursor:
            cursor.execute(query, (user_email, cutoff_date))
            return cursor.rowcount
