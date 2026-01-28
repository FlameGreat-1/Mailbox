import os
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from rich.console import Console
from rich.text import Text

from src.config import settings
from src.auth.manager import AuthManager, AuthMethod, get_auth_manager
from src.sync.manager import SyncManager, get_sync_manager
from src.services.calendar.client import CalendarClient, get_calendar_client
from src.database.models import CalendarEvent
from src.database.repositories import CalendarRepository
from src.ui.styles.theme import Theme, Symbols
from src.ui.components.header import Header
from src.ui.components.footer import Footer
from src.ui.components.inputs.text import TextInput
from src.ui.components.lists.calendar import CalendarList


class CalendarListScreen:
    EVENTS_PER_PAGE = 15

    def __init__(
        self,
        console: Console,
        auth_manager: Optional[AuthManager] = None,
        sync_manager: Optional[SyncManager] = None,
        calendar_client: Optional[CalendarClient] = None,
    ):
        self._console = console
        self._auth_manager = auth_manager or get_auth_manager()
        self._sync_manager = sync_manager or get_sync_manager()
        self._calendar_client = calendar_client or get_calendar_client()
        self._header = Header(console)
        self._footer = Footer(console)
        self._text_input = TextInput(console)
        self._calendar_list_component = CalendarList(console)
        
        self._view_mode = "upcoming"
        self._days_ahead = 7
        self._events: List[CalendarEvent] = []

    def show(self) -> Tuple[Optional[str], Optional[dict]]:
        if not self._is_calendar_available():
            return self._show_unavailable_message()

        self._load_events()

        while True:
            self._clear_screen()
            self._render_calendar()
            
            action, data = self._get_user_action()
            
            if action == "quit":
                return "quit", None
            elif action == "menu":
                return "menu", None
            elif action == "view":
                return "view_event", {"event": data}
            elif action == "refresh":
                self._refresh_events()
            elif action == "today":
                self._view_today()
            elif action == "week":
                self._view_week()
            elif action == "month":
                self._view_month()
            elif action == "search":
                self._search_events()

    def _is_calendar_available(self) -> bool:
        return self._auth_manager.active_method == AuthMethod.OAUTH

    def _show_unavailable_message(self) -> Tuple[Optional[str], Optional[dict]]:
        self._clear_screen()
        self._header.render(
            title=settings.app.app_name,
            subtitle="Calendar",
            user_email=self._auth_manager.current_email,
        )

        self._console.print()
        
        info_text = Text()
        info_text.append(f"\n  {Symbols.INFO} ", style="warning")
        info_text.append("Calendar Access Not Available\n\n", style="warning")
        info_text.append("  Calendar sync requires OAuth 2.0 authentication.\n", style="text")
        info_text.append("  You are currently using App Password authentication.\n\n", style="text.dim")
        info_text.append("  To access your Google Calendar:\n", style="text")
        info_text.append("  1. Go to Settings\n", style="text.muted")
        info_text.append("  2. Logout\n", style="text.muted")
        info_text.append("  3. Login again using OAuth 2.0\n", style="text.muted")
        self._console.print(info_text)

        self._footer.render([
            ("b", "Back"),
            ("q", "Quit"),
        ])

        self._console.print()
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append("Enter command: ", style="input.prompt")
        self._console.print(prompt_text, end="")
        
        try:
            choice = input().strip().lower()
        except (KeyboardInterrupt, EOFError):
            return "quit", None

        if choice == "q":
            return "quit", None
        
        return "menu", None

    def _load_events(self) -> None:
        user_email = self._auth_manager.current_email
        
        if not user_email:
            self._events = []
            return

        if self._view_mode == "today":
            self._events = CalendarRepository.find_today(user_email)
        elif self._view_mode == "week":
            self._events = CalendarRepository.find_upcoming(
                user_email=user_email,
                days_ahead=7,
                limit=self.EVENTS_PER_PAGE,
            )
        elif self._view_mode == "month":
            self._events = CalendarRepository.find_upcoming(
                user_email=user_email,
                days_ahead=30,
                limit=50,
            )
        else:
            self._events = CalendarRepository.find_upcoming(
                user_email=user_email,
                days_ahead=self._days_ahead,
                limit=self.EVENTS_PER_PAGE,
            )

    def _refresh_events(self) -> None:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        
        self._console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self._console,
        ) as progress:
            
            main_task = progress.add_task("[primary]Connecting...", total=100)
            
            progress.update(main_task, description="[primary]Fetching calendar events...", completed=30)
            result = self._sync_manager.sync_calendar(days_ahead=30)
            progress.update(main_task, completed=80)
            
            progress.update(main_task, description="[primary]Updating calendar...", completed=100)

        self._console.print()

        if result.success:
            self._console.print(Theme.format_status(
                f"Synced {result.total_fetched} events ({result.new_events} new)",
                "success"
            ))
        else:
            error_msg = ", ".join(result.errors) if result.errors else "Unknown error"
            self._console.print(Theme.format_status(f"Sync failed: {error_msg}", "error"))

        self._load_events()
        
        input("\nPress Enter to continue...")

    def _view_today(self) -> None:
        self._view_mode = "today"
        self._load_events()

    def _view_week(self) -> None:
        self._view_mode = "week"
        self._days_ahead = 7
        self._load_events()

    def _view_month(self) -> None:
        self._view_mode = "month"
        self._days_ahead = 30
        self._load_events()

    def _search_events(self) -> None:
        self._console.print()
        
        query = self._text_input.prompt(
            "Search events",
            required=True,
            placeholder="Enter search term",
        )

        if not query:
            return

        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Searching...", style="text")
        self._console.print(status_text)

        results = self._calendar_client.search_events(query, max_results=20)

        self._console.print()

        if results:
            self._events = results
            self._view_mode = "search"
            self._console.print(Theme.format_status(f"Found {len(results)} events", "success"))
        else:
            self._console.print(Theme.format_status("No events found", "info"))
        
        input("\nPress Enter to continue...")

    def _render_calendar(self) -> None:
        user_email = self._auth_manager.current_email
        event_count = len(self._events)

        self._header.render(
            title=settings.app.app_name,
            subtitle="Calendar",
            user_email=user_email,
        )

        view_titles = {
            "today": "Today's Events",
            "week": "This Week",
            "month": "This Month",
            "upcoming": "Upcoming Events",
            "search": "Search Results",
        }
        
        title = view_titles.get(self._view_mode, "Upcoming Events")

        self._calendar_list_component.render(
            events=self._events,
            title=title,
            show_index=True,
            group_by_date=self._view_mode != "today",
        )

        self._console.print()

        view_indicator = Text()
        view_indicator.append("  View: ", style="text.dim")
        
        views = [
            ("t", "Today", "today"),
            ("w", "Week", "week"),
            ("m", "Month", "month"),
        ]
        
        for i, (key, label, mode) in enumerate(views):
            if self._view_mode == mode:
                view_indicator.append(f"[{label}]", style="primary")
            else:
                view_indicator.append(f"[{key}]{label}", style="text.muted")
            
            if i < len(views) - 1:
                view_indicator.append("  ", style="text")
        
        self._console.print(view_indicator)

        commands = [
            ("1-9", "View"),
            ("t", "Today"),
            ("w", "Week"),
            ("m", "Month"),
            ("s", "Search"),
            ("r", "Refresh"),
            ("b", "Back"),
            ("q", "Quit"),
        ]

        self._footer.render(commands)

    def _get_user_action(self) -> Tuple[Optional[str], Optional[CalendarEvent]]:
        self._console.print()
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append("Enter command or event number: ", style="input.prompt")
        self._console.print(prompt_text, end="")
        
        try:
            choice = input().strip().lower()
        except (KeyboardInterrupt, EOFError):
            return "quit", None

        if not choice:
            return None, None

        if choice == "q":
            return "quit", None
        elif choice == "b":
            return "menu", None
        elif choice == "r":
            return "refresh", None
        elif choice == "t":
            return "today", None
        elif choice == "w":
            return "week", None
        elif choice == "m":
            return "month", None
        elif choice == "s":
            return "search", None

        try:
            index = int(choice) - 1
            if 0 <= index < len(self._events):
                return "view", self._events[index]
            else:
                self._console.print(Theme.format_status(
                    f"Invalid selection. Enter 1-{len(self._events)}",
                    "error"
                ))
                input("\nPress Enter to continue...")
                return None, None
        except ValueError:
            self._console.print(Theme.format_status("Invalid command", "error"))
            input("\nPress Enter to continue...")
            return None, None

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
