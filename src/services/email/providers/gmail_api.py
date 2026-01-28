import base64
import logging
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, formatdate
from pathlib import Path

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from src.config import settings
from src.database.models import Email

logger = logging.getLogger(__name__)


class GmailAPIProvider:
    def __init__(self, service: Resource):
        self._service = service

    @property
    def service(self) -> Resource:
        return self._service

    def fetch_messages(
        self,
        user_email: str,
        max_results: int = 50,
        label_ids: Optional[List[str]] = None,
        query: Optional[str] = None,
        include_body: bool = False,
    ) -> List[Email]:
        try:
            params = {
                "userId": "me",
                "maxResults": max_results,
            }

            if label_ids:
                params["labelIds"] = label_ids
            else:
                params["labelIds"] = ["INBOX"]

            if query:
                params["q"] = query

            response = self._service.users().messages().list(**params).execute()
            messages = response.get("messages", [])

            emails = []
            for msg_data in messages:
                email_obj = self.fetch_message(
                    msg_data["id"],
                    user_email,
                    include_body=include_body,
                )
                if email_obj:
                    emails.append(email_obj)

            return emails

        except HttpError as e:
            logger.error(f"Failed to fetch messages: {e}")
            return []

    def fetch_message(
        self,
        message_id: str,
        user_email: str,
        include_body: bool = True,
    ) -> Optional[Email]:
        try:
            format_type = "full" if include_body else "metadata"
            metadata_headers = ["From", "To", "Cc", "Subject", "Date"]

            msg = self._service.users().messages().get(
                userId="me",
                id=message_id,
                format=format_type,
                metadataHeaders=metadata_headers if not include_body else None,
            ).execute()

            return self._parse_message(msg, user_email)

        except HttpError as e:
            logger.error(f"Failed to fetch message {message_id}: {e}")
            return None

    def fetch_unread_messages(
        self,
        user_email: str,
        max_results: int = 50,
    ) -> List[Email]:
        return self.fetch_messages(
            user_email=user_email,
            max_results=max_results,
            label_ids=["INBOX", "UNREAD"],
        )

    def search_messages(
        self,
        user_email: str,
        query: str,
        max_results: int = 50,
    ) -> List[Email]:
        return self.fetch_messages(
            user_email=user_email,
            max_results=max_results,
            query=query,
            include_body=False,
        )

    def send_email(
        self,
        from_email: str,
        to_emails: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        from_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        try:
            if body_html or attachments:
                msg = MIMEMultipart("mixed")
                msg_alt = MIMEMultipart("alternative")
                msg_alt.attach(MIMEText(body_text, "plain", "utf-8"))
                if body_html:
                    msg_alt.attach(MIMEText(body_html, "html", "utf-8"))
                msg.attach(msg_alt)
            else:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body_text, "plain", "utf-8"))

            if from_name:
                msg["From"] = formataddr((from_name, from_email))
            else:
                msg["From"] = from_email

            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)

            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

            if reply_to:
                msg["Reply-To"] = reply_to

            if attachments:
                for file_path in attachments:
                    attachment = self._create_attachment(file_path)
                    if attachment:
                        msg.attach(attachment)

            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

            sent_message = self._service.users().messages().send(
                userId="me",
                body={"raw": raw_message},
            ).execute()

            logger.info(f"Email sent successfully. Message ID: {sent_message['id']}")
            return True, f"Email sent successfully"

        except HttpError as e:
            error_msg = f"Failed to send email: {e}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def send_reply(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body_text: str,
        original_message_id: str,
        thread_id: str,
        body_html: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        from_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        try:
            if body_html:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
                msg.attach(MIMEText(body_html, "html", "utf-8"))
            else:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body_text, "plain", "utf-8"))

            if from_name:
                msg["From"] = formataddr((from_name, from_email))
            else:
                msg["From"] = from_email

            msg["To"] = to_email
            msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
            msg["Date"] = formatdate(localtime=True)
            msg["In-Reply-To"] = original_message_id
            msg["References"] = original_message_id

            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

            sent_message = self._service.users().messages().send(
                userId="me",
                body={
                    "raw": raw_message,
                    "threadId": thread_id,
                },
            ).execute()

            logger.info(f"Reply sent successfully. Message ID: {sent_message['id']}")
            return True, "Reply sent successfully"

        except HttpError as e:
            error_msg = f"Failed to send reply: {e}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to send reply: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def mark_as_read(self, message_id: str) -> bool:
        try:
            self._service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return True

        except HttpError as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False

    def mark_as_unread(self, message_id: str) -> bool:
        try:
            self._service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": ["UNREAD"]},
            ).execute()
            return True

        except HttpError as e:
            logger.error(f"Failed to mark message as unread: {e}")
            return False

    def get_attachment(
        self,
        message_id: str,
        attachment_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            attachment = self._service.users().messages().attachments().get(
                userId="me",
                messageId=message_id,
                id=attachment_id,
            ).execute()

            data = base64.urlsafe_b64decode(attachment["data"])

            return {
                "data": data,
                "size": attachment.get("size", len(data)),
            }

        except HttpError as e:
            logger.error(f"Failed to get attachment: {e}")
            return None

    def get_labels(self) -> List[Dict[str, str]]:
        try:
            response = self._service.users().labels().list(userId="me").execute()
            return response.get("labels", [])

        except HttpError as e:
            logger.error(f"Failed to get labels: {e}")
            return []

    def _parse_message(self, msg: Dict[str, Any], user_email: str) -> Email:
        headers = {}
        payload = msg.get("payload", {})

        for header in payload.get("headers", []):
            headers[header["name"].lower()] = header["value"]

        body_text, body_html = self._extract_body(payload)
        attachments = self._extract_attachments_meta(payload, msg["id"])

        labels = msg.get("labelIds", [])
        is_read = "UNREAD" not in labels

        folder = "inbox"
        if "SENT" in labels:
            folder = "sent"
        elif "DRAFT" in labels:
            folder = "drafts"
        elif "SPAM" in labels:
            folder = "spam"
        elif "TRASH" in labels:
            folder = "trash"

        return Email(
            user_email=user_email,
            message_id=msg["id"],
            thread_id=msg.get("threadId"),
            from_address=self._extract_email_address(headers.get("from", "")),
            from_name=self._extract_name(headers.get("from", "")),
            to_addresses=self._parse_address_list(headers.get("to", "")),
            cc_addresses=self._parse_address_list(headers.get("cc", "")),
            subject=headers.get("subject", ""),
            body_text=body_text,
            body_html=body_html,
            date_received=self._parse_internal_date(msg.get("internalDate")),
            is_read=is_read,
            labels=labels,
            has_attachments=len(attachments) > 0,
            attachments_meta=str(attachments) if attachments else None,
            folder=folder,
        )

    def _extract_body(self, payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        body_text = None
        body_html = None

        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")

                if mime_type == "text/plain" and not body_text:
                    data = part.get("body", {}).get("data")
                    if data:
                        body_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

                elif mime_type == "text/html" and not body_html:
                    data = part.get("body", {}).get("data")
                    if data:
                        body_html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

                elif mime_type.startswith("multipart/"):
                    nested_text, nested_html = self._extract_body(part)
                    if nested_text and not body_text:
                        body_text = nested_text
                    if nested_html and not body_html:
                        body_html = nested_html
        else:
            mime_type = payload.get("mimeType", "")
            data = payload.get("body", {}).get("data")

            if data:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                if mime_type == "text/plain":
                    body_text = decoded
                elif mime_type == "text/html":
                    body_html = decoded

        return body_text, body_html

    def _extract_attachments_meta(
        self,
        payload: Dict[str, Any],
        message_id: str,
    ) -> List[Dict[str, Any]]:
        attachments = []

        def process_parts(parts: List[Dict[str, Any]]):
            for part in parts:
                filename = part.get("filename")
                if filename:
                    attachments.append({
                        "filename": filename,
                        "mime_type": part.get("mimeType"),
                        "size": part.get("body", {}).get("size", 0),
                        "attachment_id": part.get("body", {}).get("attachmentId"),
                        "message_id": message_id,
                    })

                if "parts" in part:
                    process_parts(part["parts"])

        if "parts" in payload:
            process_parts(payload["parts"])

        return attachments

    def _extract_email_address(self, value: str) -> str:
        if not value:
            return ""

        if "<" in value and ">" in value:
            start = value.rfind("<") + 1
            end = value.rfind(">")
            return value[start:end].strip()

        return value.strip()

    def _extract_name(self, value: str) -> Optional[str]:
        if not value:
            return None

        if "<" in value:
            name = value[:value.rfind("<")].strip()
            name = name.strip('"').strip("'")
            return name if name else None

        return None

    def _parse_address_list(self, value: str) -> List[str]:
        if not value:
            return []

        addresses = []
        for addr in value.split(","):
            addr = addr.strip()
            if addr:
                addresses.append(self._extract_email_address(addr))

        return addresses

    def _parse_internal_date(self, internal_date: Optional[str]) -> Optional[datetime]:
        if not internal_date:
            return None

        try:
            timestamp_ms = int(internal_date)
            return datetime.fromtimestamp(timestamp_ms / 1000)
        except Exception:
            return None

    def _create_attachment(self, file_path: str) -> Optional[MIMEBase]:
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Attachment file not found: {file_path}")
            return None

        try:
            with open(path, "rb") as f:
                file_data = f.read()

            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(file_data)
            encoders.encode_base64(attachment)

            attachment.add_header(
                "Content-Disposition",
                f"attachment; filename={path.name}",
            )

            return attachment

        except Exception as e:
            logger.error(f"Failed to create attachment from {file_path}: {e}")
            return None
