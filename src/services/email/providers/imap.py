import imaplib
import email
import logging
from typing import Optional, List, Tuple, Dict, Any
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime

from src.config import settings
from src.database.models import Email

logger = logging.getLogger(__name__)


class IMAPProvider:
    GMAIL_FOLDER_MAP = {
        "inbox": "INBOX",
        "sent": "[Gmail]/Sent Mail",
        "drafts": "[Gmail]/Drafts",
        "spam": "[Gmail]/Spam",
        "trash": "[Gmail]/Trash",
        "all": "[Gmail]/All Mail",
    }

    STANDARD_FOLDER_MAP = {
        "inbox": "INBOX",
        "sent": "Sent",
        "drafts": "Drafts",
        "spam": "Spam",
        "trash": "Trash",
        "all": "INBOX",
    }

    def __init__(self, connection: imaplib.IMAP4_SSL, use_gmail_folders: bool = True):
        self._connection = connection
        self._current_folder: Optional[str] = None
        self._folder_map = self.GMAIL_FOLDER_MAP if use_gmail_folders else self.STANDARD_FOLDER_MAP

    @property
    def connection(self) -> imaplib.IMAP4_SSL:
        return self._connection

    def select_folder(self, folder: str = "inbox") -> Tuple[bool, int]:
        imap_folder = self._folder_map.get(folder.lower(), folder)

        try:
            status, data = self._connection.select(imap_folder)

            if status == "OK":
                self._current_folder = folder
                message_count = int(data[0].decode())
                return True, message_count

            return False, 0

        except Exception as e:
            logger.error(f"Failed to select folder {folder}: {e}")
            return False, 0

    def fetch_message_ids(
        self,
        folder: str = "inbox",
        limit: int = 50,
        search_criteria: str = "ALL",
    ) -> List[str]:
        success, _ = self.select_folder(folder)
        if not success:
            return []

        try:
            status, data = self._connection.search(None, search_criteria)

            if status != "OK":
                return []

            message_ids = data[0].split()
            message_ids = list(reversed(message_ids))

            if limit:
                message_ids = message_ids[:limit]

            return [mid.decode() for mid in message_ids]

        except Exception as e:
            logger.error(f"Failed to fetch message IDs: {e}")
            return []

    def fetch_unread_message_ids(self, folder: str = "inbox", limit: int = 50) -> List[str]:
        return self.fetch_message_ids(folder, limit, "UNSEEN")

    def fetch_message(self, message_id: str, user_email: str) -> Optional[Email]:
        try:
            status, data = self._connection.fetch(message_id, "(RFC822)")

            if status != "OK" or not data or not data[0]:
                return None

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            return self._parse_message(msg, message_id, user_email)

        except Exception as e:
            logger.error(f"Failed to fetch message {message_id}: {e}")
            return None

    def fetch_message_headers(self, message_id: str, user_email: str) -> Optional[Email]:
        try:
            status, data = self._connection.fetch(
                message_id,
                "(BODY.PEEK[HEADER] FLAGS)"
            )

            if status != "OK" or not data or not data[0]:
                return None

            header_data = data[0][1]
            msg = email.message_from_bytes(header_data)

            flags = []
            if len(data[0]) > 2:
                flags_data = data[0][0].decode()
                if "\\Seen" in flags_data:
                    flags.append("\\Seen")

            email_obj = self._parse_headers(msg, message_id, user_email)

            if email_obj:
                email_obj.is_read = "\\Seen" in flags

            return email_obj

        except Exception as e:
            logger.error(f"Failed to fetch message headers {message_id}: {e}")
            return None

    def fetch_messages(
        self,
        user_email: str,
        folder: str = "inbox",
        limit: int = 50,
        headers_only: bool = False,
    ) -> List[Email]:
        message_ids = self.fetch_message_ids(folder, limit)
        emails = []

        for mid in message_ids:
            if headers_only:
                email_obj = self.fetch_message_headers(mid, user_email)
            else:
                email_obj = self.fetch_message(mid, user_email)

            if email_obj:
                email_obj.folder = folder
                emails.append(email_obj)

        return emails

    def fetch_message_body(self, message_id: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            status, data = self._connection.fetch(message_id, "(RFC822)")

            if status != "OK" or not data or not data[0]:
                return None, None

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            return self._extract_body(msg)

        except Exception as e:
            logger.error(f"Failed to fetch message body {message_id}: {e}")
            return None, None

    def mark_as_read(self, message_id: str) -> bool:
        try:
            status, _ = self._connection.store(message_id, "+FLAGS", "\\Seen")
            return status == "OK"
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False

    def mark_as_unread(self, message_id: str) -> bool:
        try:
            status, _ = self._connection.store(message_id, "-FLAGS", "\\Seen")
            return status == "OK"
        except Exception as e:
            logger.error(f"Failed to mark message as unread: {e}")
            return False

    def search_messages(
        self,
        user_email: str,
        query: str,
        folder: str = "inbox",
        limit: int = 50,
    ) -> List[Email]:
        success, _ = self.select_folder(folder)
        if not success:
            return []

        try:
            search_criteria = f'(OR SUBJECT "{query}" FROM "{query}")'
            status, data = self._connection.search(None, search_criteria)

            if status != "OK":
                return []

            message_ids = data[0].split()
            message_ids = list(reversed(message_ids))[:limit]

            emails = []
            for mid in message_ids:
                email_obj = self.fetch_message_headers(mid.decode(), user_email)
                if email_obj:
                    email_obj.folder = folder
                    emails.append(email_obj)

            return emails

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_attachment(self, message_id: str, attachment_index: int) -> Optional[Dict[str, Any]]:
        try:
            status, data = self._connection.fetch(message_id, "(RFC822)")

            if status != "OK" or not data or not data[0]:
                return None

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            attachments = []
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue

                filename = part.get_filename()
                if filename:
                    attachments.append({
                        "filename": self._decode_header_value(filename),
                        "content_type": part.get_content_type(),
                        "data": part.get_payload(decode=True),
                    })

            if attachment_index < len(attachments):
                return attachments[attachment_index]

            return None

        except Exception as e:
            logger.error(f"Failed to get attachment: {e}")
            return None

    def _parse_message(self, msg: email.message.Message, message_id: str, user_email: str) -> Email:
        body_text, body_html = self._extract_body(msg)
        attachments = self._extract_attachments_meta(msg)

        return Email(
            user_email=user_email,
            message_id=message_id,
            thread_id=msg.get("Message-ID", message_id),
            from_address=self._extract_email_address(msg.get("From", "")),
            from_name=self._extract_name(msg.get("From", "")),
            to_addresses=self._parse_address_list(msg.get("To", "")),
            cc_addresses=self._parse_address_list(msg.get("Cc", "")),
            subject=self._decode_header_value(msg.get("Subject", "")),
            body_text=body_text,
            body_html=body_html,
            date_received=self._parse_date(msg.get("Date")),
            is_read=False,
            labels=[],
            has_attachments=len(attachments) > 0,
            attachments_meta=str(attachments) if attachments else None,
        )

    def _parse_headers(self, msg: email.message.Message, message_id: str, user_email: str) -> Email:
        return Email(
            user_email=user_email,
            message_id=message_id,
            thread_id=msg.get("Message-ID", message_id),
            from_address=self._extract_email_address(msg.get("From", "")),
            from_name=self._extract_name(msg.get("From", "")),
            to_addresses=self._parse_address_list(msg.get("To", "")),
            cc_addresses=self._parse_address_list(msg.get("Cc", "")),
            subject=self._decode_header_value(msg.get("Subject", "")),
            date_received=self._parse_date(msg.get("Date")),
            is_read=False,
            labels=[],
        )

    def _extract_body(self, msg: email.message.Message) -> Tuple[Optional[str], Optional[str]]:
        body_text = None
        body_html = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        decoded = payload.decode(charset, errors="replace")

                        if content_type == "text/plain" and not body_text:
                            body_text = decoded
                        elif content_type == "text/html" and not body_html:
                            body_html = decoded
                except Exception:
                    continue
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    decoded = payload.decode(charset, errors="replace")

                    if content_type == "text/plain":
                        body_text = decoded
                    elif content_type == "text/html":
                        body_html = decoded
            except Exception:
                pass

        return body_text, body_html

    def _extract_attachments_meta(self, msg: email.message.Message) -> List[Dict[str, Any]]:
        attachments = []

        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue

            filename = part.get_filename()
            if filename:
                attachments.append({
                    "filename": self._decode_header_value(filename),
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b""),
                })

        return attachments

    def _decode_header_value(self, value: str) -> str:
        if not value:
            return ""

        try:
            decoded_parts = decode_header(value)
            result = []

            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    result.append(part.decode(charset or "utf-8", errors="replace"))
                else:
                    result.append(part)

            return "".join(result)
        except Exception:
            return value

    def _extract_email_address(self, value: str) -> str:
        if not value:
            return ""

        decoded = self._decode_header_value(value)

        if "<" in decoded and ">" in decoded:
            start = decoded.rfind("<") + 1
            end = decoded.rfind(">")
            return decoded[start:end].strip()

        return decoded.strip()

    def _extract_name(self, value: str) -> Optional[str]:
        if not value:
            return None

        decoded = self._decode_header_value(value)

        if "<" in decoded:
            name = decoded[:decoded.rfind("<")].strip()
            name = name.strip('"').strip("'")
            return name if name else None

        return None

    def _parse_address_list(self, value: str) -> List[str]:
        if not value:
            return []

        decoded = self._decode_header_value(value)
        addresses = []

        for addr in decoded.split(","):
            addr = addr.strip()
            if addr:
                addresses.append(self._extract_email_address(addr))

        return addresses

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None

        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return None
