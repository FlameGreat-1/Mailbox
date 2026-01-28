import os
from typing import Optional, Callable
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

from src.config import settings
from src.auth.manager import AuthManager, AuthMethod, get_auth_manager
from src.sync.manager import SyncManager, get_sync_manager
from src.database.repositories import EmailsRepository, CalendarRepository
from src.ui.styles.theme import Theme, Symbols
from src.ui.components.header import Header
from src.ui.components.footer import Footer
from src.ui.components.lists.email import EmailList
from src.ui.components.lists.calendar import CalendarList


class MainMenuScreen:
    def __init__(
        self,
        console: Console,
        auth_manager: Optional[AuthManager] = None,
        sync_manager: Optional[SyncManager] = None,
    ):
        self._console = console
        self._auth_manager = auth_manager or get_auth_manager()
        self._sync_manager = sync_manager or get_sync_manager()
        self._header = Header(console)
        self._footer = Footer(console)
        self._email_list = EmailList(console)
        self._calendar_list = CalendarList(console)

    def show(self) -> Optional[str]:
        while True:
            self._clear_screen()
            self._render_dashboard()
            
            choice = self._get_user_choice()
            
            if choice is None or choice == "q":
                return "quit"
            elif choice == "1" or choice == "i":
                return "inbox"
            elif choice == "2" or choice == "c":
                return "compose"
            elif choice == "3" or choice == "a":
                return "calendar"
            elif choice == "4" or choice == "s":
                return "search"
            elif choice == "5" or choice == "y":
                self._perform_sync()
            elif choice == "6" or choice == "t":
                return "settings"

    def _render_dashboard(self) -> None:
        user_email = self._auth_manager.current_email
        
        unread_count = 0
        event_count = 0
        
        if user_email:
            unread_count = EmailsRepository.get_unread_count(user_email, "inbox")
            event_count = CalendarRepository.get_event_count(user_email, 7)

        self._header.render_with_stats(
            title=settings.app.app_name,
            user_email=user_email,
            unread_count=unread_count,
            event_count=event_count,
        )

        self._console.print()
        self._render_menu_options()
        
        self._console.print()
        self._render_quick_view()

        self._footer.render([
            ("1-6", "Select"),
            ("q", "Quit"),
        ])

    def _render_menu_options(self) -> None:
        menu_items = [
            ("1", Symbols.INBOX, "Inbox", f"{self._get_unread_count()} unread"),
            ("2", Symbols.SENT, "Compose", "New email"),
            ("3", Symbols.CALENDAR, "Calendar", f"{self._get_event_count()} upcoming"),
            ("4", Symbols.BULLET, "Search", "Find emails"),
            ("5", Symbols.SYNC, "Sync", "Refresh data"),
            ("6", Symbols.BULLET, "Settings", "Preferences"),
        ]

        self._console.print("  ", end="")
        
        for i, (key, icon, label, hint) in enumerate(menu_items):
            item_text = Text()
            item_text.append(f"[{key}]", style="menu.shortcut")
            item_text.append(f" {icon} ", style="primary")
            item_text.append(label, style="menu.item")
            
            self._console.print(item_text, end="")
            
            if i < len(menu_items) - 1:
                self._console.print("   ", end="")
            
            if i == 2:
                self._console.print()
                self._console.print("  ", end="")

        self._console.print()

    def _render_quick_view(self) -> None:
        user_email = self._auth_manager.current_email
        
        if not user_email:
            return

        self._console.print(Theme.create_divider(70))
        self._console.print()

        recent_header = Text()
        recent_header.append(f"  {Symbols.MAIL_NEW} ", style="primary")
        recent_header.append("Recent Emails", style="header.subtitle")
        self._console.print(recent_header)
        self._console.print()

        recent_emails = EmailsRepository.find_by_user(
            user_email=user_email,
            folder="inbox",
            limit=3,
        )
        
        self._email_list.render_compact(recent_emails, max_items=3)

        if self._auth_manager.active_method == AuthMethod.OAUTH:
            self._console.print()
            
            calendar_header = Text()
            calendar_header.append(f"  {Symbols.CALENDAR} ", style="primary")
            calendar_header.append("Today's Events", style="header.subtitle")
            self._console.print(calendar_header)
            self._console.print()

            today_events = CalendarRepository.find_today(user_email)
            self._calendar_list.render_compact(today_events, max_items=3)

    def _get_user_choice(self) -> Optional[str]:
        self._console.print()
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append("Select option: ", style="input.prompt")
        self._console.print(prompt_text, end="")
        
        try:
            choice = input().strip().lower()
            return choice if choice else None
        except (KeyboardInterrupt, EOFError):
            return "q"

    def _perform_sync(self) -> None:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        
        self._console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self._console,
        ) as progress:
            
            main_task = progress.add_task("[primary]Initializing...", total=100)
            
            progress.update(main_task, description="[primary]Connecting...", completed=10)
            
            progress.update(main_task, description="[primary]Syncing emails...", completed=20)
            email_result = self._sync_manager.sync_emails(limit=50)
            progress.update(main_task, completed=60)
            
            calendar_result = None
            if self._sync_manager.calendar_handler.is_available():
                progress.update(main_task, description="[primary]Syncing calendar...", completed=70)
                calendar_result = self._sync_manager.sync_calendar(days_ahead=7)
                progress.update(main_task, completed=90)
            else:
                progress.update(main_task, completed=90)
            
            progress.update(main_task, description="[primary]Finalizing...", completed=100)

        self._console.print()

        summary_parts = []
        errors = []

        if email_result:
            if email_result.success:
                summary_parts.append(f"{email_result.total_fetched} emails")
            errors.extend(email_result.errors)

        if calendar_result:
            if calendar_result.success:
                summary_parts.append(f"{calendar_result.total_fetched} events")
            errors.extend(calendar_result.errors)

        if summary_parts:
            summary = ", ".join(summary_parts)
            self._console.print(Theme.format_status(f"Sync complete: {summary}", "success"))
        elif errors:
            error_msg = ", ".join(errors[:3])
            self._console.print(Theme.format_status(f"Sync failed: {error_msg}", "error"))
        else:
            self._console.print(Theme.format_status("No new data", "info"))

        input("\nPress Enter to continue...")

    def _get_unread_count(self) -> int:
        user_email = self._auth_manager.current_email
        if user_email:
            return EmailsRepository.get_unread_count(user_email, "inbox")
        return 0

    def _get_event_count(self) -> int:
        user_email = self._auth_manager.current_email
        if user_email:
            return CalendarRepository.get_event_count(user_email, 7)
        return 0

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
