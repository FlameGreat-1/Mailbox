from typing import Optional
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from src.config import settings
from src.ui.styles.theme import Theme, Colors, Symbols


class Header:
    def __init__(self, console: Console):
        self._console = console

    def render(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        user_email: Optional[str] = None,
        show_sync_status: bool = False,
        last_sync: Optional[str] = None,
    ) -> None:
        title = title or settings.app.app_name
        
        title_text = Text()
        title_text.append(f"{Symbols.MAIL} ", style="primary")
        title_text.append(title.upper(), style="header.title")
        
        if subtitle:
            title_text.append(f"  {Symbols.BULLET}  ", style="text.dim")
            title_text.append(subtitle, style="header.subtitle")

        header_content = [Align.center(title_text)]

        if user_email:
            user_line = Text()
            user_line.append(f"{Symbols.USER} ", style="text.dim")
            user_line.append(user_email, style="primary")
            
            if show_sync_status and last_sync:
                user_line.append(f"  {Symbols.BULLET}  ", style="text.dim")
                user_line.append(f"{Symbols.SYNC} Last sync: ", style="text.dim")
                user_line.append(last_sync, style="text.muted")
            
            header_content.append(Align.center(user_line))

        panel = Panel(
            Group(*header_content),
            border_style="primary",
            padding=(0, 2),
        )

        self._console.print(panel)

    def render_minimal(self, title: str) -> None:
        title_text = Text()
        title_text.append(f"{Symbols.MAIL} ", style="primary")
        title_text.append(title.upper(), style="header.title")

        self._console.print()
        self._console.print(Align.center(title_text))
        self._console.print(Theme.create_divider(60))
        self._console.print()

    def render_screen_title(self, title: str, icon: str = None) -> None:
        icon = icon or Symbols.BULLET
        
        title_text = Text()
        title_text.append(f" {icon} ", style="primary")
        title_text.append(title, style="header.title")
        title_text.append(" ", style="primary")

        self._console.print()
        self._console.print(title_text)
        self._console.print(Theme.create_divider(60))

    def render_with_stats(
        self,
        title: str,
        user_email: Optional[str] = None,
        unread_count: int = 0,
        event_count: int = 0,
    ) -> None:
        title_text = Text()
        title_text.append(f"{Symbols.MAIL} ", style="primary")
        title_text.append(title.upper(), style="header.title")

        header_content = [Align.center(title_text)]

        if user_email:
            user_line = Text()
            user_line.append(f"{Symbols.USER} ", style="text.dim")
            user_line.append(user_email, style="primary")
            header_content.append(Align.center(user_line))

        stats_line = Text()
        
        if unread_count > 0:
            stats_line.append(f"{Symbols.MAIL_NEW} ", style="email.unread")
            stats_line.append(f"{unread_count} unread", style="email.unread")
        else:
            stats_line.append(f"{Symbols.INBOX} ", style="text.dim")
            stats_line.append("No unread", style="text.dim")

        stats_line.append(f"  {Symbols.BULLET}  ", style="text.dim")

        if event_count > 0:
            stats_line.append(f"{Symbols.CALENDAR} ", style="calendar.event")
            stats_line.append(f"{event_count} upcoming", style="calendar.event")
        else:
            stats_line.append(f"{Symbols.CALENDAR} ", style="text.dim")
            stats_line.append("No events", style="text.dim")

        header_content.append(Align.center(stats_line))

        panel = Panel(
            Group(*header_content),
            border_style="primary",
            padding=(0, 2),
        )

        self._console.print(panel)
