import os
import webbrowser
from typing import Optional, Tuple
from rich.console import Console
from rich.text import Text

from src.config import settings
from src.auth.manager import AuthManager, get_auth_manager
from src.services.calendar.client import CalendarClient, get_calendar_client
from src.database.models import CalendarEvent
from src.ui.styles.theme import Theme, Symbols
from src.ui.components.header import Header
from src.ui.components.footer import Footer
from src.ui.components.inputs.text import TextInput
from src.ui.components.lists.calendar import CalendarList


class EventViewScreen:
    def __init__(
        self,
        console: Console,
        auth_manager: Optional[AuthManager] = None,
        calendar_client: Optional[CalendarClient] = None,
    ):
        self._console = console
        self._auth_manager = auth_manager or get_auth_manager()
        self._calendar_client = calendar_client or get_calendar_client()
        self._header = Header(console)
        self._footer = Footer(console)
        self._text_input = TextInput(console)
        self._calendar_list_component = CalendarList(console)
        
        self._event: Optional[CalendarEvent] = None

    def show(self, event: CalendarEvent) -> Tuple[Optional[str], Optional[dict]]:
        self._event = event

        while True:
            self._clear_screen()
            self._render_event()
            
            action = self._get_user_action()
            
            if action == "quit":
                return "quit", None
            elif action == "calendar":
                return "calendar", None
            elif action == "open_link":
                self._open_meeting_link()
            elif action == "copy_link":
                self._copy_meeting_link()

    def _render_event(self) -> None:
        self._header.render(
            title=settings.app.app_name,
            subtitle="Event Details",
            user_email=self._auth_manager.current_email,
        )

        self._calendar_list_component.render_single(self._event)

        commands = [("b", "Back")]

        if self._event.meeting_link:
            commands.insert(0, ("o", "Open Link"))
            commands.insert(1, ("c", "Copy Link"))

        commands.append(("q", "Quit"))

        self._footer.render(commands)

    def _get_user_action(self) -> Optional[str]:
        self._console.print()
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append("Enter command: ", style="input.prompt")
        self._console.print(prompt_text, end="")
        
        try:
            choice = input().strip().lower()
        except (KeyboardInterrupt, EOFError):
            return "quit"

        if not choice:
            return None

        if choice == "q":
            return "quit"
        elif choice == "b":
            return "calendar"
        elif choice == "o":
            return "open_link"
        elif choice == "c":
            return "copy_link"

        return None

    def _open_meeting_link(self) -> None:
        if not self._event.meeting_link:
            self._console.print(Theme.format_status("No meeting link available", "info"))
            input("\nPress Enter to continue...")
            return

        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LINK} ", style="info")
        status_text.append("Opening meeting link...", style="text")
        self._console.print(status_text)

        try:
            webbrowser.open(self._event.meeting_link)
            self._console.print(Theme.format_status("Meeting link opened in browser", "success"))
        except Exception as e:
            self._console.print(Theme.format_status(f"Failed to open link: {e}", "error"))
            self._console.print()
            
            link_text = Text()
            link_text.append("  Link: ", style="text.dim")
            link_text.append(self._event.meeting_link, style="link")
            self._console.print(link_text)

        input("\nPress Enter to continue...")

    def _copy_meeting_link(self) -> None:
        if not self._event.meeting_link:
            self._console.print(Theme.format_status("No meeting link available", "info"))
            input("\nPress Enter to continue...")
            return

        try:
            import pyperclip
            pyperclip.copy(self._event.meeting_link)
            self._console.print()
            self._console.print(Theme.format_status("Meeting link copied to clipboard", "success"))
        except ImportError:
            self._console.print()
            self._console.print(Theme.format_status(
                "Clipboard not available. Install pyperclip for this feature.",
                "warning"
            ))
            self._console.print()
            
            link_text = Text()
            link_text.append("  Link: ", style="text.dim")
            link_text.append(self._event.meeting_link, style="link")
            self._console.print(link_text)
        except Exception as e:
            self._console.print()
            self._console.print(Theme.format_status(f"Failed to copy: {e}", "error"))
            self._console.print()
            
            link_text = Text()
            link_text.append("  Link: ", style="text.dim")
            link_text.append(self._event.meeting_link, style="link")
            self._console.print(link_text)

        input("\nPress Enter to continue...")

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
