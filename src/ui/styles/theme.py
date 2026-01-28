from rich.style import Style
from rich.theme import Theme as RichTheme


class Colors:
    PRIMARY = "#4A90D9"
    SECONDARY = "#7B68EE"
    SUCCESS = "#50C878"
    WARNING = "#FFB347"
    ERROR = "#FF6B6B"
    INFO = "#87CEEB"
    
    TEXT = "#FFFFFF"
    TEXT_DIM = "#888888"
    TEXT_MUTED = "#666666"
    
    BG_DARK = "#1A1A2E"
    BG_MEDIUM = "#16213E"
    BG_LIGHT = "#0F3460"
    
    BORDER = "#4A4A6A"
    BORDER_FOCUS = "#4A90D9"
    
    UNREAD = "#4A90D9"
    READ = "#888888"
    
    CALENDAR_EVENT = "#9B59B6"
    CALENDAR_TODAY = "#E74C3C"
    CALENDAR_MEETING = "#3498DB"


class Symbols:
    MAIL = "✉"
    MAIL_OPEN = "📬"
    MAIL_NEW = "📩"
    INBOX = "📥"
    SENT = "📤"
    CALENDAR = "📅"
    EVENT = "📌"
    MEETING = "👥"
    
    CHECK = "✓"
    CROSS = "✗"
    ARROW_RIGHT = "→"
    ARROW_LEFT = "←"
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"
    BULLET = "•"
    STAR = "★"
    STAR_EMPTY = "☆"
    
    LOCK = "🔒"
    UNLOCK = "🔓"
    KEY = "🔑"
    USER = "👤"
    
    ATTACHMENT = "📎"
    LINK = "🔗"
    LOCATION = "📍"
    TIME = "⏰"
    
    SYNC = "🔄"
    LOADING = "⏳"
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    
    DIVIDER_H = "─"
    DIVIDER_V = "│"
    CORNER_TL = "┌"
    CORNER_TR = "┐"
    CORNER_BL = "└"
    CORNER_BR = "┘"
    
    UNREAD_DOT = "●"
    READ_DOT = "○"


class Theme:
    CUSTOM_THEME = RichTheme({
        "primary": Style(color=Colors.PRIMARY),
        "secondary": Style(color=Colors.SECONDARY),
        "success": Style(color=Colors.SUCCESS),
        "warning": Style(color=Colors.WARNING),
        "error": Style(color=Colors.ERROR),
        "info": Style(color=Colors.INFO),
        
        "text": Style(color=Colors.TEXT),
        "text.dim": Style(color=Colors.TEXT_DIM),
        "text.muted": Style(color=Colors.TEXT_MUTED),
        
        "header": Style(color=Colors.PRIMARY, bold=True),
        "header.title": Style(color=Colors.TEXT, bold=True),
        "header.subtitle": Style(color=Colors.TEXT_DIM),
        
        "menu.item": Style(color=Colors.TEXT),
        "menu.item.selected": Style(color=Colors.PRIMARY, bold=True),
        "menu.item.disabled": Style(color=Colors.TEXT_MUTED),
        "menu.shortcut": Style(color=Colors.SECONDARY),
        
        "email.unread": Style(color=Colors.UNREAD, bold=True),
        "email.read": Style(color=Colors.READ),
        "email.subject": Style(color=Colors.TEXT),
        "email.from": Style(color=Colors.PRIMARY),
        "email.date": Style(color=Colors.TEXT_DIM),
        "email.preview": Style(color=Colors.TEXT_MUTED),
        
        "calendar.event": Style(color=Colors.CALENDAR_EVENT),
        "calendar.today": Style(color=Colors.CALENDAR_TODAY, bold=True),
        "calendar.meeting": Style(color=Colors.CALENDAR_MEETING),
        "calendar.time": Style(color=Colors.TEXT_DIM),
        "calendar.location": Style(color=Colors.TEXT_MUTED),
        
        "input.label": Style(color=Colors.TEXT),
        "input.prompt": Style(color=Colors.PRIMARY),
        "input.text": Style(color=Colors.TEXT),
        "input.placeholder": Style(color=Colors.TEXT_MUTED),
        "input.error": Style(color=Colors.ERROR),
        
        "border": Style(color=Colors.BORDER),
        "border.focus": Style(color=Colors.BORDER_FOCUS),
        
        "status.success": Style(color=Colors.SUCCESS),
        "status.error": Style(color=Colors.ERROR),
        "status.warning": Style(color=Colors.WARNING),
        "status.info": Style(color=Colors.INFO),
        
        "link": Style(color=Colors.INFO, underline=True),
        "highlight": Style(color=Colors.WARNING, bold=True),
    })

    @staticmethod
    def get_theme() -> RichTheme:
        return Theme.CUSTOM_THEME

    @staticmethod
    def style_unread_indicator(is_read: bool) -> str:
        if is_read:
            return f"[text.dim]{Symbols.READ_DOT}[/text.dim]"
        return f"[email.unread]{Symbols.UNREAD_DOT}[/email.unread]"

    @staticmethod
    def style_email_row(is_read: bool) -> str:
        return "email.read" if is_read else "email.unread"

    @staticmethod
    def format_shortcut(key: str, description: str) -> str:
        return f"[menu.shortcut][{key}][/menu.shortcut] {description}"

    @staticmethod
    def format_status(message: str, status_type: str = "info") -> str:
        symbol_map = {
            "success": Symbols.SUCCESS,
            "error": Symbols.ERROR,
            "warning": Symbols.WARNING,
            "info": Symbols.INFO,
        }
        symbol = symbol_map.get(status_type, Symbols.INFO)
        return f"[status.{status_type}]{symbol} {message}[/status.{status_type}]"

    @staticmethod
    def create_divider(width: int = 60, char: str = None) -> str:
        char = char or Symbols.DIVIDER_H
        return f"[border]{char * width}[/border]"

    @staticmethod
    def create_box_top(width: int = 60) -> str:
        return f"[border]{Symbols.CORNER_TL}{Symbols.DIVIDER_H * (width - 2)}{Symbols.CORNER_TR}[/border]"

    @staticmethod
    def create_box_bottom(width: int = 60) -> str:
        return f"[border]{Symbols.CORNER_BL}{Symbols.DIVIDER_H * (width - 2)}{Symbols.CORNER_BR}[/border]"

    @staticmethod
    def create_box_row(content: str, width: int = 60) -> str:
        content_len = len(content)
        padding = width - content_len - 4
        if padding < 0:
            content = content[:width - 7] + "..."
            padding = 0
        return f"[border]{Symbols.DIVIDER_V}[/border] {content}{' ' * padding} [border]{Symbols.DIVIDER_V}[/border]"
