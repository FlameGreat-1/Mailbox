import os
from typing import Optional, List, Tuple
from rich.console import Console
from rich.text import Text

from src.config import settings
from src.auth.manager import AuthManager, get_auth_manager
from src.sync.manager import SyncManager, get_sync_manager
from src.services.email.client import EmailClient, get_email_client
from src.database.models import Email
from src.database.repositories import EmailsRepository
from src.ui.styles.theme import Theme, Symbols
from src.ui.components.header import Header
from src.ui.components.footer import Footer
from src.ui.components.inputs.text import TextInput
from src.ui.components.lists.email import EmailList


class InboxListScreen:
    EMAILS_PER_PAGE = 15

    def __init__(
        self,
        console: Console,
        auth_manager: Optional[AuthManager] = None,
        sync_manager: Optional[SyncManager] = None,
        email_client: Optional[EmailClient] = None,
    ):
        self._console = console
        self._auth_manager = auth_manager or get_auth_manager()
        self._sync_manager = sync_manager or get_sync_manager()
        self._email_client = email_client or get_email_client()
        self._header = Header(console)
        self._footer = Footer(console)
        self._text_input = TextInput(console)
        self._email_list_component = EmailList(console)
        
        self._current_page = 1
        self._total_pages = 1
        self._emails: List[Email] = []
        self._selected_index: Optional[int] = None

    def show(self) -> Tuple[Optional[str], Optional[dict]]:
        self._load_emails()
        
        while True:
            self._clear_screen()
            self._render_inbox()
            
            action, data = self._get_user_action()
            
            if action == "quit":
                return "quit", None
            elif action == "menu":
                return "menu", None
            elif action == "view":
                return "view_email", {"email": data}
            elif action == "compose":
                return "compose", None
            elif action == "reply":
                return "compose", {"reply_to": data}
            elif action == "search":
                return "search", None
            elif action == "refresh":
                self._refresh_emails()
            elif action == "next_page":
                self._next_page()
            elif action == "prev_page":
                self._prev_page()

    def _load_emails(self) -> None:
        user_email = self._auth_manager.current_email
        
        if not user_email:
            self._emails = []
            return

        total_count = EmailsRepository.get_total_count(user_email, "inbox")
        self._total_pages = max(1, (total_count + self.EMAILS_PER_PAGE - 1) // self.EMAILS_PER_PAGE)
        
        offset = (self._current_page - 1) * self.EMAILS_PER_PAGE
        
        self._emails = EmailsRepository.find_by_user(
            user_email=user_email,
            folder="inbox",
            limit=self.EMAILS_PER_PAGE,
            offset=offset,
        )

    def _refresh_emails(self) -> None:
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
            
            progress.update(main_task, description="[primary]Fetching emails...", completed=30)
            result = self._sync_manager.sync_emails(limit=50)
            progress.update(main_task, completed=80)
            
            progress.update(main_task, description="[primary]Updating inbox...", completed=100)

        self._console.print()

        if result.success:
            self._console.print(Theme.format_status(
                f"Synced {result.total_fetched} emails ({result.new_emails} new)",
                "success"
            ))
        else:
            error_msg = ", ".join(result.errors) if result.errors else "Unknown error"
            self._console.print(Theme.format_status(f"Sync failed: {error_msg}", "error"))

        self._current_page = 1
        self._load_emails()
        
        input("\nPress Enter to continue...")

    def _next_page(self) -> None:
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_emails()

    def _prev_page(self) -> None:
        if self._current_page > 1:
            self._current_page -= 1
            self._load_emails()

    def _render_inbox(self) -> None:
        user_email = self._auth_manager.current_email
        unread_count = EmailsRepository.get_unread_count(user_email, "inbox") if user_email else 0

        self._header.render(
            title=settings.app.app_name,
            subtitle="Inbox",
            user_email=user_email,
        )

        self._email_list_component.render(
            emails=self._emails,
            title="Inbox",
            show_index=True,
            page=self._current_page,
            total_pages=self._total_pages,
            unread_count=unread_count,
        )

        commands = [
            ("1-9", "Open"),
            ("c", "Compose"),
            ("r", "Refresh"),
        ]
        
        if self._current_page > 1:
            commands.append(("p", "Prev"))
        
        if self._current_page < self._total_pages:
            commands.append(("n", "Next"))
        
        commands.extend([
            ("s", "Search"),
            ("b", "Back"),
            ("q", "Quit"),
        ])

        self._footer.render(commands)

    def _get_user_action(self) -> Tuple[Optional[str], Optional[Email]]:
        self._console.print()
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append("Enter command or email number: ", style="input.prompt")
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
        elif choice == "c":
            return "compose", None
        elif choice == "r":
            return "refresh", None
        elif choice == "s":
            return "search", None
        elif choice == "n":
            return "next_page", None
        elif choice == "p":
            return "prev_page", None

        try:
            index = int(choice) - 1
            if 0 <= index < len(self._emails):
                return "view", self._emails[index]
            else:
                self._console.print(Theme.format_status(
                    f"Invalid selection. Enter 1-{len(self._emails)}",
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


class SearchScreen:
    MAX_RESULTS = 50

    def __init__(
        self,
        console: Console,
        auth_manager: Optional[AuthManager] = None,
        email_client: Optional[EmailClient] = None,
    ):
        self._console = console
        self._auth_manager = auth_manager or get_auth_manager()
        self._email_client = email_client or get_email_client()
        self._header = Header(console)
        self._footer = Footer(console)
        self._text_input = TextInput(console)
        self._email_list_component = EmailList(console)
        
        self._search_query: str = ""
        self._results: List[Email] = []

    def show(self) -> Tuple[Optional[str], Optional[dict]]:
        self._clear_screen()
        self._header.render(
            title=settings.app.app_name,
            subtitle="Search Emails",
            user_email=self._auth_manager.current_email,
        )

        self._console.print()
        
        query = self._text_input.prompt(
            "Search",
            required=True,
            placeholder="Enter search term",
        )

        if not query:
            return "inbox", None

        self._search_query = query
        self._perform_search()

        while True:
            self._clear_screen()
            self._render_results()
            
            action, data = self._get_user_action()
            
            if action == "quit":
                return "quit", None
            elif action == "inbox":
                return "inbox", None
            elif action == "view":
                return "view_email", {"email": data}
            elif action == "new_search":
                return "search", None

    def _perform_search(self) -> None:
        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Searching...", style="text")
        self._console.print(status_text)

        self._results = self._email_client.search_emails(
            query=self._search_query,
            limit=self.MAX_RESULTS,
        )

    def _render_results(self) -> None:
        self._header.render(
            title=settings.app.app_name,
            subtitle="Search Results",
            user_email=self._auth_manager.current_email,
        )

        self._email_list_component.render_search_results(
            emails=self._results,
            query=self._search_query,
            total_results=len(self._results),
        )

        self._footer.render([
            ("1-9", "Open"),
            ("n", "New Search"),
            ("b", "Back"),
            ("q", "Quit"),
        ])

    def _get_user_action(self) -> Tuple[Optional[str], Optional[Email]]:
        self._console.print()
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append("Enter command or email number: ", style="input.prompt")
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
            return "inbox", None
        elif choice == "n":
            return "new_search", None

        try:
            index = int(choice) - 1
            if 0 <= index < len(self._results):
                return "view", self._results[index]
            else:
                self._console.print(Theme.format_status(
                    f"Invalid selection. Enter 1-{len(self._results)}",
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
