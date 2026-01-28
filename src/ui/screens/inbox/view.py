import os
from typing import Optional, Tuple
from pathlib import Path
from rich.console import Console
from rich.text import Text

from src.config import settings
from src.auth.manager import AuthManager, get_auth_manager
from src.services.email.client import EmailClient, get_email_client
from src.services.email.parser import EmailParser
from src.database.models import Email
from src.ui.styles.theme import Theme, Symbols
from src.ui.components.header import Header
from src.ui.components.footer import Footer
from src.ui.components.inputs.text import TextInput
from src.ui.components.lists.email import EmailList


class EmailViewScreen:
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
        
        self._email: Optional[Email] = None

    def show(self, email: Email) -> Tuple[Optional[str], Optional[dict]]:
        self._email = email
        
        if not self._email.body_text and not self._email.body_html:
            self._fetch_full_email()

        self._mark_as_read()

        while True:
            self._clear_screen()
            self._render_email()
            
            action, data = self._get_user_action()
            
            if action == "quit":
                return "quit", None
            elif action == "inbox":
                return "inbox", None
            elif action == "reply":
                return "compose", {"reply_to": self._email}
            elif action == "forward":
                return "compose", {"forward": self._email}
            elif action == "attachment":
                self._save_attachment(data)
            elif action == "toggle_read":
                self._toggle_read_status()

    def _fetch_full_email(self) -> None:
        if self._email.body_text or self._email.body_html:
            return
        
        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Loading email content...", style="text")
        self._console.print(status_text)

        try:
            full_email = self._email_client.get_email(self._email.message_id, from_db=False)
            
            if full_email:
                self._email = full_email
        except Exception as e:
            self._console.print()
            self._console.print(Theme.format_status(f"Failed to load email: {str(e)}", "error"))
            input("\nPress Enter to continue...")

    def _mark_as_read(self) -> None:
        if not self._email.is_read:
            self._email_client.mark_as_read(self._email.message_id)
            self._email.is_read = True

    def _toggle_read_status(self) -> None:
        if self._email.is_read:
            self._email_client.mark_as_unread(self._email.message_id)
            self._email.is_read = False
            self._console.print(Theme.format_status("Marked as unread", "success"))
        else:
            self._email_client.mark_as_read(self._email.message_id)
            self._email.is_read = True
            self._console.print(Theme.format_status("Marked as read", "success"))
        
        input("\nPress Enter to continue...")

    def _render_email(self) -> None:
        self._header.render(
            title=settings.app.app_name,
            subtitle="View Email",
            user_email=self._auth_manager.current_email,
        )

        self._email_list_component.render_single(self._email)

        commands = [
            ("r", "Reply"),
            ("f", "Forward"),
        ]

        if self._email.has_attachments:
            commands.append(("a", "Attachments"))

        if self._email.is_read:
            commands.append(("u", "Mark Unread"))
        else:
            commands.append(("m", "Mark Read"))

        commands.extend([
            ("b", "Back"),
            ("q", "Quit"),
        ])

        self._footer.render(commands)

    def _get_user_action(self) -> Tuple[Optional[str], Optional[int]]:
        self._console.print()
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append("Enter command: ", style="input.prompt")
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
        elif choice == "r":
            return "reply", None
        elif choice == "f":
            return "forward", None
        elif choice == "a":
            return "attachment", None
        elif choice == "u" or choice == "m":
            return "toggle_read", None

        return None, None

    def _save_attachment(self, attachment_index: Optional[int] = None) -> None:
        if not self._email.has_attachments:
            self._console.print(Theme.format_status("No attachments in this email", "info"))
            input("\nPress Enter to continue...")
            return

        attachments = EmailParser.parse_attachments_meta(self._email.attachments_meta)
        
        if not attachments:
            self._console.print(Theme.format_status("No attachments found", "info"))
            input("\nPress Enter to continue...")
            return

        self._clear_screen()
        self._header.render_screen_title("Save Attachment", Symbols.ATTACHMENT)

        self._console.print()
        self._console.print("  Available attachments:", style="text.dim")
        self._console.print()

        for i, attachment in enumerate(attachments):
            filename = attachment.get("filename", "Unknown")
            size = attachment.get("size", 0)
            size_str = EmailParser.format_file_size(size)
            
            attach_text = Text()
            attach_text.append(f"  [{i + 1}] ", style="menu.shortcut")
            attach_text.append(f"{Symbols.ATTACHMENT} ", style="primary")
            attach_text.append(filename, style="text")
            attach_text.append(f" ({size_str})", style="text.muted")
            self._console.print(attach_text)

        self._console.print()

        choice = self._text_input.prompt_number(
            "Select attachment",
            min_value=1,
            max_value=len(attachments),
        )

        if choice is None:
            return

        attachment_index = choice - 1

        self._console.print()
        
        save_path = self._text_input.prompt(
            "Save to directory",
            default=str(Path.home() / "Downloads"),
            required=True,
        )

        if not save_path:
            return

        save_dir = Path(save_path)
        
        if not save_dir.exists():
            create_dir = self._text_input.prompt_confirm(
                f"Directory '{save_path}' doesn't exist. Create it?",
                default=True,
            )
            
            if create_dir:
                try:
                    save_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self._console.print(Theme.format_status(f"Failed to create directory: {e}", "error"))
                    input("\nPress Enter to continue...")
                    return
            else:
                return

        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Saving attachment...", style="text")
        self._console.print(status_text)

        success, message = self._email_client.save_attachment(
            message_id=self._email.message_id,
            attachment_index=attachment_index,
            save_path=str(save_dir),
        )

        self._console.print()

        if success:
            self._console.print(Theme.format_status(message, "success"))
        else:
            self._console.print(Theme.format_status(message, "error"))

        input("\nPress Enter to continue...")

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
