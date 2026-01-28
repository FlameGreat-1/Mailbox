from typing import List, Tuple, Optional
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

from src.ui.styles.theme import Theme, Symbols


class Footer:
    def __init__(self, console: Console):
        self._console = console

    def render(self, commands: List[Tuple[str, str]], columns: int = 4) -> None:
        command_texts = []
        
        for key, description in commands:
            cmd_text = Text()
            cmd_text.append(f"[{key}]", style="menu.shortcut")
            cmd_text.append(f" {description}", style="text.dim")
            command_texts.append(cmd_text)

        self._console.print()
        self._console.print(Theme.create_divider(60))
        
        rows = [command_texts[i:i + columns] for i in range(0, len(command_texts), columns)]
        
        for row in rows:
            padded_row = []
            for cmd in row:
                padded_cmd = Text()
                padded_cmd.append_text(cmd)
                padding_needed = 18 - len(cmd.plain)
                if padding_needed > 0:
                    padded_cmd.append(" " * padding_needed)
                padded_row.append(padded_cmd)
            
            row_text = Text()
            for i, cmd in enumerate(padded_row):
                row_text.append_text(cmd)
                if i < len(padded_row) - 1:
                    row_text.append("  ")
            
            self._console.print(row_text)

    def render_simple(self, message: str) -> None:
        self._console.print()
        self._console.print(Theme.create_divider(60))
        
        footer_text = Text()
        footer_text.append(message, style="text.dim")
        
        self._console.print(footer_text)

    def render_navigation(
        self,
        can_go_back: bool = True,
        can_go_forward: bool = False,
        extra_commands: Optional[List[Tuple[str, str]]] = None,
    ) -> None:
        commands = []
        
        if can_go_back:
            commands.append(("b", "Back"))
        
        if can_go_forward:
            commands.append(("n", "Next"))
        
        if extra_commands:
            commands.extend(extra_commands)
        
        commands.append(("q", "Quit"))
        
        self.render(commands)

    def render_with_status(
        self,
        commands: List[Tuple[str, str]],
        status_message: str,
        status_type: str = "info",
    ) -> None:
        self._console.print()
        self._console.print(Theme.create_divider(60))
        
        status_text = Theme.format_status(status_message, status_type)
        self._console.print(status_text)
        
        self._console.print()
        
        command_texts = []
        for key, description in commands:
            cmd_text = Text()
            cmd_text.append(f"[{key}]", style="menu.shortcut")
            cmd_text.append(f" {description}", style="text.dim")
            command_texts.append(cmd_text)

        row_text = Text()
        for i, cmd in enumerate(command_texts):
            row_text.append_text(cmd)
            if i < len(command_texts) - 1:
                row_text.append("  |  ", style="text.muted")
        
        self._console.print(row_text)

    def render_pagination(
        self,
        current_page: int,
        total_pages: int,
        extra_commands: Optional[List[Tuple[str, str]]] = None,
    ) -> None:
        commands = []
        
        if current_page > 1:
            commands.append(("p", "Previous"))
        
        if current_page < total_pages:
            commands.append(("n", "Next"))
        
        if extra_commands:
            commands.extend(extra_commands)
        
        commands.append(("b", "Back"))
        commands.append(("q", "Quit"))

        self._console.print()
        self._console.print(Theme.create_divider(60))
        
        page_text = Text()
        page_text.append(f"Page {current_page} of {total_pages}", style="text.dim")
        self._console.print(page_text)
        
        self._console.print()
        
        command_texts = []
        for key, description in commands:
            cmd_text = Text()
            cmd_text.append(f"[{key}]", style="menu.shortcut")
            cmd_text.append(f" {description}", style="text.dim")
            command_texts.append(cmd_text)

        row_text = Text()
        for i, cmd in enumerate(command_texts):
            row_text.append_text(cmd)
            if i < len(command_texts) - 1:
                row_text.append("  ")
        
        self._console.print(row_text)

    def render_confirm(self, message: str = "Press Enter to continue...") -> None:
        self._console.print()
        self._console.print(Theme.create_divider(60))
        
        confirm_text = Text()
        confirm_text.append(message, style="text.dim")
        
        self._console.print(confirm_text)
