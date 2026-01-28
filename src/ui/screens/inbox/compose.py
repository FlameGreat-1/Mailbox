import os
from typing import Optional, Tuple, List
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

from src.config import settings
from src.auth.manager import AuthManager, get_auth_manager
from src.services.email.client import EmailClient, get_email_client
from src.services.email.parser import EmailParser
from src.database.models import Email
from src.ui.styles.theme import Theme, Symbols
from src.ui.components.header import Header
from src.ui.components.footer import Footer
from src.ui.components.inputs.text import TextInput


class ComposeScreen:
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
        
        self._to_emails: List[str] = []
        self._cc_emails: List[str] = []
        self._subject: str = ""
        self._body: str = ""
        self._reply_to: Optional[Email] = None
        self._forward: Optional[Email] = None

    def show(
        self,
        reply_to: Optional[Email] = None,
        forward: Optional[Email] = None,
    ) -> Tuple[Optional[str], Optional[dict]]:
        self._reply_to = reply_to
        self._forward = forward
        
        self._reset_fields()
        
        if reply_to:
            self._setup_reply()
        elif forward:
            self._setup_forward()

        return self._compose_flow()

    def _reset_fields(self) -> None:
        self._to_emails = []
        self._cc_emails = []
        self._subject = ""
        self._body = ""

    def _setup_reply(self) -> None:
        if self._reply_to:
            self._to_emails = [EmailParser.extract_reply_address(self._reply_to)]
            
            subject = self._reply_to.subject or ""
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"
            self._subject = subject

    def _setup_forward(self) -> None:
        if self._forward:
            subject = self._forward.subject or ""
            if not subject.lower().startswith("fwd:"):
                subject = f"Fwd: {subject}"
            self._subject = subject
            
            original_body = EmailParser.get_display_body(self._forward)
            self._body = (
                f"\n\n---------- Forwarded message ----------\n"
                f"From: {EmailParser.format_email_address(self._forward.from_address, self._forward.from_name)}\n"
                f"Date: {EmailParser.format_date(self._forward.date_received)}\n"
                f"Subject: {self._forward.subject}\n"
                f"To: {', '.join(self._forward.to_addresses)}\n\n"
                f"{original_body}"
            )

    def _compose_flow(self) -> Tuple[Optional[str], Optional[dict]]:
        self._clear_screen()
        
        mode = "Reply" if self._reply_to else ("Forward" if self._forward else "Compose")
        
        self._header.render(
            title=settings.app.app_name,
            subtitle=f"{mode} Email",
            user_email=self._auth_manager.current_email,
        )

        self._console.print()
        
        from_text = Text()
        from_text.append(f"  {Symbols.MAIL} From: ", style="text.dim")
        from_text.append(self._auth_manager.current_email or "", style="primary")
        from_text.append(" (cannot be changed)", style="text.muted")
        self._console.print(from_text)

        self._console.print()
        self._console.print(Theme.create_divider(60))
        self._console.print()

        if not self._to_emails:
            to_emails = self._text_input.prompt_email_list("To", required=True)
            
            if not to_emails:
                return self._handle_cancel()
            
            self._to_emails = to_emails
        else:
            to_text = Text()
            to_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
            to_text.append("To: ", style="input.label")
            to_text.append(", ".join(self._to_emails), style="text")
            self._console.print(to_text)
            self._console.print()
            
            change_to = self._text_input.prompt_confirm(
                "Change recipient?",
                default=False,
            )
            
            if change_to:
                to_emails = self._text_input.prompt_email_list("To", required=True)
                if to_emails:
                    self._to_emails = to_emails

        self._console.print()
        
        add_cc = self._text_input.prompt_confirm("Add CC recipients?", default=False)
        
        if add_cc:
            cc_emails = self._text_input.prompt_email_list("CC", required=False)
            if cc_emails:
                self._cc_emails = cc_emails

        self._console.print()

        if not self._subject:
            subject = self._text_input.prompt(
                "Subject",
                required=False,
                placeholder="Enter subject",
            )
            self._subject = subject or ""
        else:
            subject_text = Text()
            subject_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
            subject_text.append("Subject: ", style="input.label")
            subject_text.append(self._subject, style="text")
            self._console.print(subject_text)
            self._console.print()
            
            change_subject = self._text_input.prompt_confirm(
                "Change subject?",
                default=False,
            )
            
            if change_subject:
                new_subject = self._text_input.prompt(
                    "Subject",
                    default=self._subject,
                    required=False,
                )
                if new_subject is not None:
                    self._subject = new_subject

        self._console.print()

        if self._reply_to:
            self._console.print("  Original message will be quoted below your reply.", style="text.muted")
            self._console.print()

        body = self._text_input.prompt_multiline(
            "Message body",
            end_marker=".",
            required=True,
        )

        if body is None:
            return self._handle_cancel()

        if self._reply_to:
            body = body + EmailParser.create_reply_body(self._reply_to)
        elif self._forward and self._body:
            body = body + self._body

        self._body = body

        return self._confirm_and_send()

    def _confirm_and_send(self) -> Tuple[Optional[str], Optional[dict]]:
        self._clear_screen()
        self._header.render_screen_title("Confirm Email", Symbols.MAIL)

        self._console.print()

        preview_content = []

        from_line = Text()
        from_line.append("From: ", style="text.dim")
        from_line.append(self._auth_manager.current_email or "", style="primary")
        preview_content.append(from_line)

        to_line = Text()
        to_line.append("To: ", style="text.dim")
        to_line.append(", ".join(self._to_emails), style="text")
        preview_content.append(to_line)

        if self._cc_emails:
            cc_line = Text()
            cc_line.append("CC: ", style="text.dim")
            cc_line.append(", ".join(self._cc_emails), style="text")
            preview_content.append(cc_line)

        subject_line = Text()
        subject_line.append("Subject: ", style="text.dim")
        subject_line.append(self._subject or "(No Subject)", style="text")
        preview_content.append(subject_line)

        preview_content.append(Text())
        preview_content.append(Text("─" * 50, style="border"))
        preview_content.append(Text())

        body_preview = self._body[:500]
        if len(self._body) > 500:
            body_preview += "..."
        
        for line in body_preview.split("\n")[:15]:
            preview_content.append(Text(line, style="text"))

        if len(self._body.split("\n")) > 15:
            preview_content.append(Text("...", style="text.muted"))

        content = Text("\n").join(preview_content)

        self._console.print(Panel(
            content,
            border_style="primary",
            title=f"{Symbols.MAIL} Email Preview",
            title_align="left",
            padding=(1, 2),
        ))

        self._console.print()

        self._footer.render([
            ("s", "Send"),
            ("e", "Edit"),
            ("c", "Cancel"),
        ])

        self._console.print()
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append("Enter command: ", style="input.prompt")
        self._console.print(prompt_text, end="")
        
        try:
            choice = input().strip().lower()
        except (KeyboardInterrupt, EOFError):
            return self._handle_cancel()

        if choice == "s":
            return self._send_email()
        elif choice == "e":
            return self._compose_flow()
        elif choice == "c":
            return self._handle_cancel()
        else:
            return self._confirm_and_send()

    def _send_email(self) -> Tuple[Optional[str], Optional[dict]]:
        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Sending email...", style="text")
        self._console.print(status_text)

        if self._reply_to:
            success, message = self._email_client.send_reply(
                original_email=self._reply_to,
                body_text=self._body,
                cc_emails=self._cc_emails if self._cc_emails else None,
                include_original=False,
            )
        else:
            success, message = self._email_client.send_email(
                to_emails=self._to_emails,
                subject=self._subject,
                body_text=self._body,
                cc_emails=self._cc_emails if self._cc_emails else None,
            )

        self._console.print()

        if success:
            self._console.print(Theme.format_status("Email sent successfully!", "success"))
        else:
            self._console.print(Theme.format_status(f"Failed to send: {message}", "error"))

        input("\nPress Enter to continue...")

        return "inbox", None

    def _handle_cancel(self) -> Tuple[Optional[str], Optional[dict]]:
        self._console.print()
        
        if self._to_emails or self._subject or self._body:
            discard = self._text_input.prompt_confirm(
                "Discard this email?",
                default=False,
            )
            
            if not discard:
                return self._compose_flow()

        return "inbox", None

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
