import os
import sys
import logging
from typing import Optional
from rich.console import Console

from src.config import settings
from src.auth.manager import AuthManager, get_auth_manager
from src.sync.manager import SyncManager, get_sync_manager
from src.services.email.client import EmailClient, get_email_client
from src.services.calendar.client import CalendarClient, get_calendar_client
from src.database.repositories import EmailsRepository

from src.ui.styles.theme import Theme, Symbols
from src.ui.screens.login import LoginScreen
from src.ui.screens.menu import MainMenuScreen
from src.ui.screens.settings import SettingsScreen
from src.ui.screens.inbox.list import InboxListScreen, SearchScreen
from src.ui.screens.inbox.view import EmailViewScreen
from src.ui.screens.inbox.compose import ComposeScreen
from src.ui.screens.calendar.list import CalendarListScreen
from src.ui.screens.calendar.view import EventViewScreen

logger = logging.getLogger(__name__)


class MailboxApp:
    def __init__(self):
        self._console = Console(theme=Theme.get_theme())
        self._auth_manager = get_auth_manager()
        self._sync_manager = get_sync_manager()
        self._email_client = get_email_client()
        self._calendar_client = get_calendar_client()
        
        self._current_screen = "login"  
        self._screen_data = {}
        self._running = False

    def run(self) -> None:
        self._running = True
        self._setup_logging()
        self._show_startup_progress()
        
        try:
            self._main_loop()
        except KeyboardInterrupt:
            self._handle_exit()
        except Exception as e:
            logger.error(f"Application error: {e}")
            self._console.print(f"\n[error]Application error: {e}[/error]")
            raise
        finally:
            self._cleanup()

    def _show_startup_progress(self) -> None:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        import time
        
        self._clear_screen()
        
        self._console.print()
        self._console.print(f"  [primary]{Symbols.MAIL}[/primary] [bold]MAILBOX[/bold]")
        self._console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self._console,
            transient=False,
        ) as progress:
            
            task = progress.add_task("[primary]Starting...", total=100)
            
            progress.update(task, description="[primary]Loading configuration...", completed=20)
            time.sleep(0.1)
            
            progress.update(task, description="[primary]Connecting to database...", completed=40)
            from src.database.connection import test_connection
            test_connection()
            progress.update(task, completed=60)
            
            progress.update(task, description="[primary]Initializing services...", completed=80)
            time.sleep(0.1)
            
            progress.update(task, description="[primary]Ready!", completed=100)

        self._console.print()

    def _main_loop(self) -> None:
        while self._running:
            next_screen, data = self._handle_screen()
            
            if next_screen == "quit":
                self._running = False
            else:
                self._current_screen = next_screen
                self._screen_data = data or {}

    def _handle_screen(self) -> tuple:
        screen_handlers = {
            "login": self._handle_login,
            "menu": self._handle_menu,
            "inbox": self._handle_inbox,
            "view_email": self._handle_view_email,
            "compose": self._handle_compose,
            "search": self._handle_search,
            "calendar": self._handle_calendar,
            "view_event": self._handle_view_event,
            "settings": self._handle_settings,
        }

        handler = screen_handlers.get(self._current_screen, self._handle_menu)
        return handler()

    def _handle_login(self) -> tuple:
        """
        ALWAYS show login screen - no auto-login.
        User must explicitly enter credentials every time app starts.
        """
        screen = LoginScreen(self._console, self._auth_manager)
        success, email = screen.show()

        if success and email:
            self._perform_initial_sync()
            return "menu", None
        
        return "quit", None

    def _handle_menu(self) -> tuple:
        screen = MainMenuScreen(
            self._console,
            self._auth_manager,
            self._sync_manager,
        )
        result = screen.show()

        if result == "quit":
            return "quit", None
        elif result == "inbox":
            return "inbox", None
        elif result == "compose":
            return "compose", None
        elif result == "calendar":
            return "calendar", None
        elif result == "search":
            return "search", None
        elif result == "settings":
            return "settings", None

        return "menu", None

    def _handle_inbox(self) -> tuple:
        screen = InboxListScreen(
            self._console,
            self._auth_manager,
            self._sync_manager,
            self._email_client,
        )
        result, data = screen.show()

        if result == "quit":
            return "quit", None
        elif result == "menu":
            return "menu", None
        elif result == "view_email":
            return "view_email", data
        elif result == "compose":
            return "compose", data
        elif result == "search":
            return "search", None

        return "inbox", None

    def _handle_view_email(self) -> tuple:
        email = self._screen_data.get("email")
        
        if not email:
            return "inbox", None

        screen = EmailViewScreen(
            self._console,
            self._auth_manager,
            self._email_client,
        )
        result, data = screen.show(email)

        if result == "quit":
            return "quit", None
        elif result == "inbox":
            return "inbox", None
        elif result == "compose":
            return "compose", data

        return "inbox", None

    def _handle_compose(self) -> tuple:
        reply_to = self._screen_data.get("reply_to")
        forward = self._screen_data.get("forward")

        screen = ComposeScreen(
            self._console,
            self._auth_manager,
            self._email_client,
        )
        result, data = screen.show(reply_to=reply_to, forward=forward)

        if result == "quit":
            return "quit", None

        return "inbox", None

    def _handle_search(self) -> tuple:
        screen = SearchScreen(
            self._console,
            self._auth_manager,
            self._email_client,
        )
        result, data = screen.show()

        if result == "quit":
            return "quit", None
        elif result == "inbox":
            return "inbox", None
        elif result == "view_email":
            return "view_email", data
        elif result == "search":
            return "search", None

        return "inbox", None

    def _handle_calendar(self) -> tuple:
        screen = CalendarListScreen(
            self._console,
            self._auth_manager,
            self._sync_manager,
            self._calendar_client,
        )
        result, data = screen.show()

        if result == "quit":
            return "quit", None
        elif result == "menu":
            return "menu", None
        elif result == "view_event":
            return "view_event", data

        return "calendar", None

    def _handle_view_event(self) -> tuple:
        event = self._screen_data.get("event")
        
        if not event:
            return "calendar", None

        screen = EventViewScreen(
            self._console,
            self._auth_manager,
            self._calendar_client,
        )
        result, data = screen.show(event)

        if result == "quit":
            return "quit", None
        elif result == "calendar":
            return "calendar", None

        return "calendar", None

    def _handle_settings(self) -> tuple:
        screen = SettingsScreen(
            self._console,
            self._auth_manager,
            self._sync_manager,
        )
        result = screen.show()

        if result == "quit":
            return "quit", None
        elif result == "login":
            return "login", None

        return "menu", None

    def _perform_initial_sync(self) -> None:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        
        user_email = self._auth_manager.current_email
        existing_emails = EmailsRepository.get_total_count(user_email, "inbox") if user_email else 0
        
        self._clear_screen()
        self._console.print()
        
        if existing_emails > 0:
            self._console.print(f"  [info]{Symbols.SYNC}[/info] [text]Checking for new emails...[/text]")
        else:
            self._console.print(f"  [info]{Symbols.SYNC}[/info] [text]Performing initial sync...[/text]")
        
        self._console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self._console,
            transient=False,
        ) as progress:
            
            main_task = progress.add_task("[primary]Connecting to email server...", total=100)
            progress.update(main_task, completed=10)
            
            progress.update(main_task, description="[primary]Fetching emails...")
            email_result = self._sync_manager.sync_emails(limit=20)
            progress.update(main_task, completed=60)
            
            calendar_result = None
            if self._calendar_client.is_calendar_available():
                progress.update(main_task, description="[primary]Fetching calendar events...")
                calendar_result = self._sync_manager.sync_calendar(days_ahead=30)
            progress.update(main_task, completed=100, description="[primary]Complete!")

        self._console.print()

        summary_parts = []
        errors = []

        if email_result and email_result.success:
            if email_result.new_emails > 0:
                summary_parts.append(f"{email_result.new_emails} new emails")
            else:
                summary_parts.append("No new emails")
            errors.extend(email_result.errors)

        if calendar_result and calendar_result.success:
            if calendar_result.new_events > 0:
                summary_parts.append(f"{calendar_result.new_events} new events")
            errors.extend(calendar_result.errors)

        if summary_parts:
            summary = ", ".join(summary_parts)
            self._console.print(f"  [success]{Symbols.SUCCESS}[/success] [text]Sync complete: {summary}[/text]")
        else:
            self._console.print(f"  [warning]{Symbols.WARNING}[/warning] [text]Sync completed with some issues[/text]")

        if errors:
            for error in errors[:3]:
                self._console.print(f"    [text.dim]• {error}[/text.dim]")

        self._console.print()
        input("  Press Enter to continue...")

    def _handle_exit(self) -> None:
        self._clear_screen()
        self._console.print()
        self._console.print(f"  [primary]{Symbols.MAIL}[/primary] [text]Thank you for using {settings.app.app_name}![/text]")
        self._console.print()

    def _cleanup(self) -> None:
        """
        Clean up resources when app closes.
        Note: We logout from session but keep credentials in database.
        """
        if self._auth_manager.is_authenticated:
            self._auth_manager.logout()  

    def _setup_logging(self) -> None:
        log_level = os.getenv("LOG_LEVEL", "WARNING").upper()
        
        logging.basicConfig(
            level=getattr(logging, log_level, logging.WARNING),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("mailbox.log", mode="a"),
            ]
        )

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")


def run_app() -> None:
    app = MailboxApp()
    app.run()
