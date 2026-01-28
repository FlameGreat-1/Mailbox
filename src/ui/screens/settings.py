import os
from typing import Optional
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

from src.config import settings
from src.auth.manager import AuthManager, AuthMethod, get_auth_manager
from src.sync.manager import SyncManager, get_sync_manager
from src.database.repositories import EmailsRepository, CalendarRepository
from src.ui.styles.theme import Theme, Symbols
from src.ui.components.header import Header
from src.ui.components.footer import Footer
from src.ui.components.inputs.text import TextInput


class SettingsScreen:
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
        self._text_input = TextInput(console)

    def show(self) -> Optional[str]:
        while True:
            self._clear_screen()
            self._render_settings()
            
            choice = self._get_user_choice()
            
            if choice is None or choice == "b":
                return "menu"
            elif choice == "q":
                return "quit"
            elif choice == "1":
                self._show_account_info()
            elif choice == "2":
                self._show_sync_status()
            elif choice == "3":
                self._clear_local_data()
            elif choice == "4":
                result = self._logout()
                if result == "login":
                    return "login"

    def _render_settings(self) -> None:
        self._header.render(
            title=settings.app.app_name,
            subtitle="Settings",
            user_email=self._auth_manager.current_email,
        )

        self._console.print()

        menu_items = [
            ("1", Symbols.USER, "Account Info", "View account details"),
            ("2", Symbols.SYNC, "Sync Status", "View sync information"),
            ("3", Symbols.BULLET, "Clear Local Data", "Remove cached data"),
            ("4", Symbols.UNLOCK, "Logout", "Sign out and clear credentials"),
        ]

        for key, icon, label, hint in menu_items:
            item_text = Text()
            item_text.append(f"  [{key}] ", style="menu.shortcut")
            item_text.append(f"{icon} ", style="primary")
            item_text.append(f"{label:20}", style="menu.item")
            item_text.append(f" - {hint}", style="text.muted")
            self._console.print(item_text)

        self._footer.render([
            ("1-4", "Select"),
            ("b", "Back"),
            ("q", "Quit"),
        ])

    def _show_account_info(self) -> None:
        self._clear_screen()
        self._header.render_screen_title("Account Information", Symbols.USER)

        self._console.print()

        user_email = self._auth_manager.current_email
        auth_method = self._auth_manager.active_method

        info_items = [
            ("Email", user_email or "Not logged in"),
            ("Auth Method", auth_method.value.replace("_", " ").title() if auth_method else "None"),
            ("App Version", settings.app.version),
        ]

        if user_email:
            email_count = EmailsRepository.get_total_count(user_email, "inbox")
            unread_count = EmailsRepository.get_unread_count(user_email, "inbox")
            event_count = CalendarRepository.get_event_count(user_email, 30)
            
            info_items.extend([
                ("", ""),
                ("Total Emails (Inbox)", str(email_count)),
                ("Unread Emails", str(unread_count)),
                ("Upcoming Events (30 days)", str(event_count)),
            ])

        for label, value in info_items:
            if not label:
                self._console.print()
                continue
                
            info_text = Text()
            info_text.append(f"  {label}: ", style="text.dim")
            info_text.append(value, style="text")
            self._console.print(info_text)

        if auth_method == AuthMethod.OAUTH:
            self._console.print()
            oauth_text = Text()
            oauth_text.append(f"  {Symbols.CHECK} ", style="success")
            oauth_text.append("Calendar access enabled", style="text.dim")
            self._console.print(oauth_text)
        elif auth_method == AuthMethod.APP_PASSWORD:
            self._console.print()
            app_pass_text = Text()
            app_pass_text.append(f"  {Symbols.INFO} ", style="info")
            app_pass_text.append(
                "Calendar access requires OAuth authentication",
                style="text.dim"
            )
            self._console.print(app_pass_text)

        self._console.print()
        input("Press Enter to continue...")

    def _show_sync_status(self) -> None:
        self._clear_screen()
        self._header.render_screen_title("Sync Status", Symbols.SYNC)

        self._console.print()

        status = self._sync_manager.get_sync_status()

        sync_text = Text()
        sync_text.append("  Currently Syncing: ", style="text.dim")
        sync_text.append(
            "Yes" if status["syncing"] else "No",
            style="warning" if status["syncing"] else "text"
        )
        self._console.print(sync_text)

        last_sync_text = Text()
        last_sync_text.append("  Last Full Sync: ", style="text.dim")
        last_sync_text.append(
            status["last_full_sync"] or "Never",
            style="text"
        )
        self._console.print(last_sync_text)

        self._console.print()
        self._console.print("  Email Sync:", style="primary")
        
        email_status = status.get("email", {})
        
        email_last_sync = Text()
        email_last_sync.append("    Last Sync: ", style="text.dim")
        email_last_sync.append(
            email_status.get("last_sync") or "Never",
            style="text"
        )
        self._console.print(email_last_sync)

        email_count = Text()
        email_count.append("    Inbox Count: ", style="text.dim")
        email_count.append(str(email_status.get("inbox_count", 0)), style="text")
        self._console.print(email_count)

        email_unread = Text()
        email_unread.append("    Unread: ", style="text.dim")
        email_unread.append(str(email_status.get("unread_count", 0)), style="text")
        self._console.print(email_unread)

        self._console.print()
        self._console.print("  Calendar Sync:", style="primary")
        
        calendar_status = status.get("calendar", {})
        
        cal_available = Text()
        cal_available.append("    Available: ", style="text.dim")
        cal_available.append(
            "Yes" if calendar_status.get("available") else "No",
            style="success" if calendar_status.get("available") else "text.muted"
        )
        self._console.print(cal_available)

        if calendar_status.get("available"):
            cal_last_sync = Text()
            cal_last_sync.append("    Last Sync: ", style="text.dim")
            cal_last_sync.append(
                calendar_status.get("last_sync") or "Never",
                style="text"
            )
            self._console.print(cal_last_sync)

            cal_upcoming = Text()
            cal_upcoming.append("    Upcoming Events: ", style="text.dim")
            cal_upcoming.append(str(calendar_status.get("upcoming_count", 0)), style="text")
            self._console.print(cal_upcoming)

            cal_today = Text()
            cal_today.append("    Today's Events: ", style="text.dim")
            cal_today.append(str(calendar_status.get("today_count", 0)), style="text")
            self._console.print(cal_today)

        self._console.print()
        input("Press Enter to continue...")

    def _clear_local_data(self) -> None:
        self._clear_screen()
        self._header.render_screen_title("Clear Local Data", Symbols.WARNING)

        self._console.print()
        
        warning_panel = Panel(
            Text.from_markup(
                f"[warning]{Symbols.WARNING} Warning[/warning]\n\n"
                f"[text]This will delete all locally cached emails and calendar events.[/text]\n"
                f"[text.dim]Your credentials will be preserved.[/text.dim]\n"
                f"[text.dim]Data will be re-synced from Gmail on next sync.[/text.dim]"
            ),
            border_style="warning",
            padding=(1, 2),
        )
        self._console.print(warning_panel)

        self._console.print()
        
        confirm = self._text_input.prompt_confirm(
            "Are you sure you want to clear all local data?",
            default=False,
        )

        if confirm:
            self._console.print()
            
            status_text = Text()
            status_text.append(f"{Symbols.LOADING} ", style="info")
            status_text.append("Clearing local data...", style="text")
            self._console.print(status_text)

            result = self._sync_manager.clear_all_local_data()

            self._console.print()
            self._console.print(Theme.format_status(
                f"Cleared {result['emails_deleted']} emails and {result['events_deleted']} events",
                "success"
            ))
        else:
            self._console.print()
            self._console.print(Theme.format_status("Operation cancelled", "info"))

        self._console.print()
        input("Press Enter to continue...")

    def _logout(self) -> Optional[str]:
        self._clear_screen()
        self._header.render_screen_title("Logout", Symbols.UNLOCK)

        self._console.print()
        
        warning_panel = Panel(
            Text.from_markup(
                f"[warning]{Symbols.WARNING} Warning[/warning]\n\n"
                f"[text]This will:[/text]\n"
                f"[text.dim]• Sign you out of your account[/text.dim]\n"
                f"[text.dim]• Delete your stored credentials[/text.dim]\n"
                f"[text.dim]• Clear all local email and calendar data[/text.dim]\n\n"
                f"[text]You will need to login again to use the app.[/text]"
            ),
            border_style="warning",
            padding=(1, 2),
        )
        self._console.print(warning_panel)

        self._console.print()
        
        confirm = self._text_input.prompt_confirm(
            "Are you sure you want to logout?",
            default=False,
        )

        if confirm:
            self._console.print()
            
            status_text = Text()
            status_text.append(f"{Symbols.LOADING} ", style="info")
            status_text.append("Logging out...", style="text")
            self._console.print(status_text)

            self._sync_manager.clear_all_local_data()
            self._auth_manager.logout_and_clear()

            self._console.print()
            self._console.print(Theme.format_status("Logged out successfully", "success"))
            
            self._console.print()
            input("Press Enter to continue...")
            
            return "login"
        else:
            self._console.print()
            self._console.print(Theme.format_status("Logout cancelled", "info"))
            
            self._console.print()
            input("Press Enter to continue...")
            
            return None

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

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
