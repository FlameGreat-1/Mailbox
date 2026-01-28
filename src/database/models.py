from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class AuthType(Enum):
    OAUTH = "oauth"
    APP_PASSWORD = "app_password"


@dataclass
class Credential:
    id: Optional[int] = None
    user_email: str = ""
    auth_type: AuthType = AuthType.APP_PASSWORD
    encrypted_token: str = ""
    access_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: dict) -> "Credential":
        return cls(
            id=row.get("id"),
            user_email=row.get("user_email", ""),
            auth_type=AuthType(row.get("auth_type", "app_password")),
            encrypted_token=row.get("encrypted_token", ""),
            access_token=row.get("access_token"),
            token_expiry=row.get("token_expiry"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_email": self.user_email,
            "auth_type": self.auth_type.value,
            "encrypted_token": self.encrypted_token,
            "access_token": self.access_token,
            "token_expiry": self.token_expiry,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Email:
    id: Optional[int] = None
    user_email: str = ""
    message_id: str = ""
    thread_id: Optional[str] = None
    from_address: str = ""
    from_name: Optional[str] = None
    to_addresses: List[str] = field(default_factory=list)
    cc_addresses: List[str] = field(default_factory=list)
    subject: str = ""
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    date_received: Optional[datetime] = None
    is_read: bool = False
    labels: List[str] = field(default_factory=list)
    has_attachments: bool = False
    attachments_meta: Optional[str] = None
    folder: str = "inbox"
    synced_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: dict) -> "Email":
        import json

        to_addresses = row.get("to_addresses", "[]")
        if isinstance(to_addresses, str):
            to_addresses = json.loads(to_addresses) if to_addresses else []

        cc_addresses = row.get("cc_addresses", "[]")
        if isinstance(cc_addresses, str):
            cc_addresses = json.loads(cc_addresses) if cc_addresses else []

        labels = row.get("labels", "[]")
        if isinstance(labels, str):
            labels = json.loads(labels) if labels else []

        return cls(
            id=row.get("id"),
            user_email=row.get("user_email", ""),
            message_id=row.get("message_id", ""),
            thread_id=row.get("thread_id"),
            from_address=row.get("from_address", ""),
            from_name=row.get("from_name"),
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            subject=row.get("subject", ""),
            body_text=row.get("body_text"),
            body_html=row.get("body_html"),
            date_received=row.get("date_received"),
            is_read=bool(row.get("is_read", False)),
            labels=labels,
            has_attachments=bool(row.get("has_attachments", False)),
            attachments_meta=row.get("attachments_meta"),
            folder=row.get("folder", "inbox"),
            synced_at=row.get("synced_at"),
        )

    def to_dict(self) -> dict:
        import json

        return {
            "id": self.id,
            "user_email": self.user_email,
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "from_address": self.from_address,
            "from_name": self.from_name,
            "to_addresses": json.dumps(self.to_addresses),
            "cc_addresses": json.dumps(self.cc_addresses),
            "subject": self.subject,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "date_received": self.date_received,
            "is_read": self.is_read,
            "labels": json.dumps(self.labels),
            "has_attachments": self.has_attachments,
            "attachments_meta": self.attachments_meta,
            "folder": self.folder,
            "synced_at": self.synced_at,
        }


@dataclass
class CalendarEvent:
    id: Optional[int] = None
    user_email: str = ""
    event_id: str = ""
    calendar_id: str = "primary"
    title: str = ""
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    attendees: List[str] = field(default_factory=list)
    meeting_link: Optional[str] = None
    status: str = "confirmed"
    synced_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: dict) -> "CalendarEvent":
        import json

        attendees = row.get("attendees", "[]")
        if isinstance(attendees, str):
            attendees = json.loads(attendees) if attendees else []

        return cls(
            id=row.get("id"),
            user_email=row.get("user_email", ""),
            event_id=row.get("event_id", ""),
            calendar_id=row.get("calendar_id", "primary"),
            title=row.get("title", ""),
            description=row.get("description"),
            location=row.get("location"),
            start_time=row.get("start_time"),
            end_time=row.get("end_time"),
            is_all_day=bool(row.get("is_all_day", False)),
            attendees=attendees,
            meeting_link=row.get("meeting_link"),
            status=row.get("status", "confirmed"),
            synced_at=row.get("synced_at"),
        )

    def to_dict(self) -> dict:
        import json

        return {
            "id": self.id,
            "user_email": self.user_email,
            "event_id": self.event_id,
            "calendar_id": self.calendar_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "is_all_day": self.is_all_day,
            "attendees": json.dumps(self.attendees),
            "meeting_link": self.meeting_link,
            "status": self.status,
            "synced_at": self.synced_at,
        }
