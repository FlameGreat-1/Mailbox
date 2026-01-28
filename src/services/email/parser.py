import re
import html
import logging
from typing import Optional, List, Dict, Any
from html.parser import HTMLParser
from io import StringIO

logger = logging.getLogger(__name__)


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()
        self._skip_data = False
        self._skip_tags = {"script", "style", "head", "meta", "link"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip_data = True
        elif tag == "br":
            self.text.write("\n")
        elif tag in ("p", "div", "tr", "li"):
            self.text.write("\n")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip_data = False
        elif tag in ("p", "div", "table", "ul", "ol"):
            self.text.write("\n")

    def handle_data(self, data):
        if not self._skip_data:
            self.text.write(data)

    def get_data(self):
        return self.text.getvalue()


class EmailParser:
    @staticmethod
    def html_to_text(html_content: str) -> str:
        if not html_content:
            return ""

        try:
            stripper = HTMLStripper()
            stripper.feed(html_content)
            text = stripper.get_data()

            text = html.unescape(text)
            text = re.sub(r"\n\s*\n", "\n\n", text)
            text = re.sub(r" +", " ", text)
            text = "\n".join(line.strip() for line in text.splitlines())
            text = re.sub(r"\n{3,}", "\n\n", text)

            return text.strip()

        except Exception as e:
            logger.error(f"Failed to convert HTML to text: {e}")
            return html_content

    @staticmethod
    def get_display_body(email_obj) -> str:
        if email_obj.body_text:
            return email_obj.body_text.strip()

        if email_obj.body_html:
            return EmailParser.html_to_text(email_obj.body_html)

        return ""

    @staticmethod
    def get_preview(email_obj, max_length: int = 100) -> str:
        body = EmailParser.get_display_body(email_obj)

        if not body:
            return ""

        body = " ".join(body.split())

        if len(body) <= max_length:
            return body

        return body[:max_length].rsplit(" ", 1)[0] + "..."

    @staticmethod
    def format_email_address(email: str, name: Optional[str] = None) -> str:
        if name:
            return f"{name} <{email}>"
        return email

    @staticmethod
    def parse_email_address(value: str) -> Dict[str, Optional[str]]:
        if not value:
            return {"email": "", "name": None}

        value = value.strip()

        if "<" in value and ">" in value:
            match = re.match(r"^(.+?)\s*<(.+?)>$", value)
            if match:
                name = match.group(1).strip().strip('"').strip("'")
                email = match.group(2).strip()
                return {"email": email, "name": name if name else None}

        return {"email": value, "name": None}

    @staticmethod
    def format_date(dt, format_str: str = "%b %d, %Y %I:%M %p") -> str:
        if not dt:
            return ""

        try:
            return dt.strftime(format_str)
        except Exception:
            return str(dt)

    @staticmethod
    def format_date_short(dt) -> str:
        return EmailParser.format_date(dt, "%b %d")

    @staticmethod
    def format_date_relative(dt) -> str:
        if not dt:
            return ""

        from datetime import datetime, timedelta

        now = datetime.now()

        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        diff = now - dt

        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days}d ago"
        elif dt.year == now.year:
            return dt.strftime("%b %d")
        else:
            return dt.strftime("%b %d, %Y")

    @staticmethod
    def truncate_subject(subject: str, max_length: int = 50) -> str:
        if not subject:
            return "(No Subject)"

        subject = subject.strip()

        if len(subject) <= max_length:
            return subject

        return subject[:max_length - 3] + "..."

    @staticmethod
    def parse_attachments_meta(meta_str: Optional[str]) -> List[Dict[str, Any]]:
        if not meta_str:
            return []

        try:
            import ast
            return ast.literal_eval(meta_str)
        except Exception:
            return []

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    @staticmethod
    def create_reply_body(original_email, include_original: bool = True) -> str:
        lines = ["\n\n"]

        if include_original:
            lines.append(f"On {EmailParser.format_date(original_email.date_received)}, ")
            lines.append(f"{original_email.from_name or original_email.from_address} wrote:\n")
            lines.append("-" * 40 + "\n")

            original_body = EmailParser.get_display_body(original_email)
            quoted_lines = [f"> {line}" for line in original_body.splitlines()]
            lines.append("\n".join(quoted_lines))

        return "".join(lines)

    @staticmethod
    def extract_reply_address(email_obj) -> str:
        return email_obj.from_address

    @staticmethod
    def is_valid_email(email: str) -> bool:
        if not email:
            return False

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email.strip()))

    @staticmethod
    def validate_email_list(emails: List[str]) -> List[str]:
        return [e.strip() for e in emails if EmailParser.is_valid_email(e.strip())]
