from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

from src.database.models import Email
from src.services.email.parser import EmailParser
from src.ui.styles.theme import Theme, Symbols, Colors


class EmailList:
    def __init__(self, console: Console):
        self._console = console

    def render(
        self,
        emails: List[Email],
        title: str = "Inbox",
        show_index: bool = True,
        selected_index: Optional[int] = None,
        page: int = 1,
        total_pages: int = 1,
        unread_count: int = 0,
    ) -> None:
        header_text = Text()
        header_text.append(f"{Symbols.INBOX} ", style="primary")
        header_text.append(title, style="header.title")
        
        if unread_count > 0:
            header_text.append(f" ({unread_count} unread)", style="email.unread")

        self._console.print()
        self._console.print(header_text)
        self._console.print(Theme.create_divider(70))

        if not emails:
            empty_text = Text()
            empty_text.append("\n  No emails found\n", style="text.muted")
            self._console.print(empty_text)
            return

        table = Table(
            show_header=True,
            header_style="primary",
            border_style="border",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        if show_index:
            table.add_column("#", style="text.dim", width=4, justify="right")
        
        table.add_column("", width=2)
        table.add_column("From", style="email.from", width=22, no_wrap=True)
        table.add_column("Subject", style="email.subject", ratio=1)
        table.add_column("Date", style="email.date", width=12, justify="right")

        for i, email in enumerate(emails):
            index_str = str(i + 1) if show_index else ""
            
            status_indicator = Theme.style_unread_indicator(email.is_read)
            
            from_display = email.from_name or email.from_address
            if len(from_display) > 20:
                from_display = from_display[:17] + "..."
            
            subject_display = EmailParser.truncate_subject(email.subject, 40)
            
            if email.has_attachments:
                subject_display = f"{Symbols.ATTACHMENT} {subject_display}"
            
            date_display = EmailParser.format_date_relative(email.date_received)
            
            row_style = Theme.style_email_row(email.is_read)
            
            if selected_index is not None and i == selected_index:
                row_style = "highlight"

            if show_index:
                table.add_row(
                    index_str,
                    status_indicator,
                    from_display,
                    subject_display,
                    date_display,
                    style=row_style if email.is_read else None,
                )
            else:
                table.add_row(
                    status_indicator,
                    from_display,
                    subject_display,
                    date_display,
                    style=row_style if email.is_read else None,
                )

        self._console.print(table)

        if total_pages > 1:
            self._console.print()
            page_text = Text()
            page_text.append(f"Page {page} of {total_pages}", style="text.dim")
            self._console.print(page_text)

    def render_compact(
        self,
        emails: List[Email],
        max_items: int = 5,
    ) -> None:
        if not emails:
            empty_text = Text()
            empty_text.append("  No recent emails", style="text.muted")
            self._console.print(empty_text)
            return

        display_emails = emails[:max_items]

        for i, email in enumerate(display_emails):
            row_text = Text()
            
            row_text.append(f"  {Theme.style_unread_indicator(email.is_read)} ")
            
            from_display = email.from_name or email.from_address
            if len(from_display) > 15:
                from_display = from_display[:12] + "..."
            
            if email.is_read:
                row_text.append(from_display, style="email.read")
            else:
                row_text.append(from_display, style="email.unread")
            
            row_text.append(" - ", style="text.dim")
            
            subject = EmailParser.truncate_subject(email.subject, 30)
            row_text.append(subject, style="text.dim" if email.is_read else "text")
            
            self._console.print(row_text)

        if len(emails) > max_items:
            more_text = Text()
            more_text.append(f"  ... and {len(emails) - max_items} more", style="text.muted")
            self._console.print(more_text)

    def render_single(self, email: Email) -> None:
        header_panel_content = []

        from_text = Text()
        from_text.append("From: ", style="text.dim")
        from_text.append(
            EmailParser.format_email_address(email.from_address, email.from_name),
            style="email.from"
        )
        header_panel_content.append(from_text)

        to_text = Text()
        to_text.append("To: ", style="text.dim")
        to_text.append(", ".join(email.to_addresses), style="text")
        header_panel_content.append(to_text)

        if email.cc_addresses:
            cc_text = Text()
            cc_text.append("Cc: ", style="text.dim")
            cc_text.append(", ".join(email.cc_addresses), style="text")
            header_panel_content.append(cc_text)

        date_text = Text()
        date_text.append("Date: ", style="text.dim")
        date_text.append(EmailParser.format_date(email.date_received), style="email.date")
        header_panel_content.append(date_text)

        subject_text = Text()
        subject_text.append("Subject: ", style="text.dim")
        subject_text.append(email.subject or "(No Subject)", style="header.title")
        header_panel_content.append(subject_text)

        if email.has_attachments:
            attachments = EmailParser.parse_attachments_meta(email.attachments_meta)
            attach_text = Text()
            attach_text.append(f"{Symbols.ATTACHMENT} Attachments: ", style="text.dim")
            attach_names = [a.get("filename", "Unknown") for a in attachments]
            attach_text.append(", ".join(attach_names), style="info")
            header_panel_content.append(attach_text)

        header_content = Text("\n").join(header_panel_content)
        
        self._console.print(Panel(
            header_content,
            border_style="primary",
            title=f"{Symbols.MAIL_OPEN} Email Details",
            title_align="left",
        ))

        self._console.print()
        self._console.print(Theme.create_divider(70))
        self._console.print()

        body = EmailParser.get_display_body(email)
        
        if body:
            for line in body.split("\n"):
                self._console.print(f"  {line}")
        else:
            self._console.print("  (No content)", style="text.muted")

        self._console.print()
        self._console.print(Theme.create_divider(70))

    def render_search_results(
        self,
        emails: List[Email],
        query: str,
        total_results: int,
    ) -> None:
        header_text = Text()
        header_text.append(f"{Symbols.BULLET} ", style="primary")
        header_text.append("Search Results for: ", style="text.dim")
        header_text.append(f'"{query}"', style="highlight")
        header_text.append(f" ({total_results} found)", style="text.muted")

        self._console.print()
        self._console.print(header_text)
        self._console.print(Theme.create_divider(70))

        if not emails:
            empty_text = Text()
            empty_text.append("\n  No emails match your search\n", style="text.muted")
            self._console.print(empty_text)
            return

        self.render(emails, title="", show_index=True)
