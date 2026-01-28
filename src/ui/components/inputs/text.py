from typing import Optional, Callable, List
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt

from src.ui.styles.theme import Theme, Symbols


class TextInput:
    def __init__(self, console: Console):
        self._console = console

    def prompt(
        self,
        label: str,
        default: Optional[str] = None,
        required: bool = True,
        validator: Optional[Callable[[str], bool]] = None,
        error_message: str = "Invalid input",
        placeholder: Optional[str] = None,
    ) -> Optional[str]:
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append(label, style="input.label")
        
        if not required:
            prompt_text.append(" (optional)", style="text.muted")
        
        if placeholder:
            prompt_text.append(f" [{placeholder}]", style="input.placeholder")
        
        prompt_text.append(": ", style="input.prompt")

        while True:
            self._console.print(prompt_text, end="")
            
            try:
                value = input().strip()
            except (KeyboardInterrupt, EOFError):
                self._console.print()
                return None

            if not value and default is not None:
                return default

            if not value and required:
                self._console.print(
                    Theme.format_status("This field is required", "error")
                )
                continue

            if not value and not required:
                return None

            if validator and not validator(value):
                self._console.print(Theme.format_status(error_message, "error"))
                continue

            return value

    def prompt_multiline(
        self,
        label: str,
        end_marker: str = ".",
        required: bool = True,
    ) -> Optional[str]:
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append(label, style="input.label")
        
        if not required:
            prompt_text.append(" (optional)", style="text.muted")

        self._console.print(prompt_text)
        
        hint_text = Text()
        hint_text.append(f"  Enter '{end_marker}' on a new line to finish", style="text.muted")
        self._console.print(hint_text)
        self._console.print()

        lines = []
        
        while True:
            try:
                line = input()
            except (KeyboardInterrupt, EOFError):
                self._console.print()
                return None

            if line.strip() == end_marker:
                break
            
            lines.append(line)

        content = "\n".join(lines).strip()

        if not content and required:
            self._console.print(Theme.format_status("This field is required", "error"))
            return self.prompt_multiline(label, end_marker, required)

        if not content and not required:
            return None

        return content

    def prompt_email(
        self,
        label: str = "Email",
        required: bool = True,
    ) -> Optional[str]:
        def validate_email(value: str) -> bool:
            import re
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return bool(re.match(pattern, value))

        return self.prompt(
            label=label,
            required=required,
            validator=validate_email,
            error_message="Please enter a valid email address",
            placeholder="user@example.com",
        )

    def prompt_email_list(
        self,
        label: str = "Recipients",
        required: bool = True,
    ) -> List[str]:
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append(label, style="input.label")
        
        if not required:
            prompt_text.append(" (optional)", style="text.muted")
        
        prompt_text.append(" [comma-separated]", style="input.placeholder")
        prompt_text.append(": ", style="input.prompt")

        while True:
            self._console.print(prompt_text, end="")
            
            try:
                value = input().strip()
            except (KeyboardInterrupt, EOFError):
                self._console.print()
                return []

            if not value and required:
                self._console.print(
                    Theme.format_status("At least one recipient is required", "error")
                )
                continue

            if not value:
                return []

            emails = [e.strip() for e in value.split(",") if e.strip()]
            
            import re
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            
            valid_emails = []
            invalid_emails = []
            
            for email in emails:
                if re.match(pattern, email):
                    valid_emails.append(email)
                else:
                    invalid_emails.append(email)

            if invalid_emails:
                self._console.print(
                    Theme.format_status(
                        f"Invalid email(s): {', '.join(invalid_emails)}",
                        "error"
                    )
                )
                continue

            if not valid_emails and required:
                self._console.print(
                    Theme.format_status("At least one valid recipient is required", "error")
                )
                continue

            return valid_emails

    def prompt_choice(
        self,
        label: str,
        choices: List[str],
        default: Optional[int] = None,
    ) -> Optional[int]:
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append(label, style="input.label")
        self._console.print(prompt_text)
        self._console.print()

        for i, choice in enumerate(choices, 1):
            choice_text = Text()
            choice_text.append(f"  [{i}] ", style="menu.shortcut")
            choice_text.append(choice, style="menu.item")
            
            if default is not None and i == default:
                choice_text.append(" (default)", style="text.muted")
            
            self._console.print(choice_text)

        self._console.print()

        while True:
            select_text = Text()
            select_text.append("Select option: ", style="input.prompt")
            self._console.print(select_text, end="")
            
            try:
                value = input().strip()
            except (KeyboardInterrupt, EOFError):
                self._console.print()
                return None

            if not value and default is not None:
                return default

            try:
                choice_num = int(value)
                if 1 <= choice_num <= len(choices):
                    return choice_num
                else:
                    self._console.print(
                        Theme.format_status(
                            f"Please enter a number between 1 and {len(choices)}",
                            "error"
                        )
                    )
            except ValueError:
                self._console.print(
                    Theme.format_status("Please enter a valid number", "error")
                )

    def prompt_confirm(
        self,
        message: str,
        default: bool = False,
    ) -> bool:
        default_hint = "Y/n" if default else "y/N"
        
        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append(message, style="input.label")
        prompt_text.append(f" [{default_hint}]: ", style="input.prompt")

        self._console.print(prompt_text, end="")
        
        try:
            value = input().strip().lower()
        except (KeyboardInterrupt, EOFError):
            self._console.print()
            return default

        if not value:
            return default

        return value in ("y", "yes", "true", "1")

    def prompt_number(
        self,
        label: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        default: Optional[int] = None,
    ) -> Optional[int]:
        range_hint = ""
        if min_value is not None and max_value is not None:
            range_hint = f" ({min_value}-{max_value})"
        elif min_value is not None:
            range_hint = f" (min: {min_value})"
        elif max_value is not None:
            range_hint = f" (max: {max_value})"

        prompt_text = Text()
        prompt_text.append(f"{Symbols.ARROW_RIGHT} ", style="primary")
        prompt_text.append(label, style="input.label")
        prompt_text.append(range_hint, style="input.placeholder")
        prompt_text.append(": ", style="input.prompt")

        while True:
            self._console.print(prompt_text, end="")
            
            try:
                value = input().strip()
            except (KeyboardInterrupt, EOFError):
                self._console.print()
                return None

            if not value and default is not None:
                return default

            try:
                num = int(value)
                
                if min_value is not None and num < min_value:
                    self._console.print(
                        Theme.format_status(f"Value must be at least {min_value}", "error")
                    )
                    continue
                
                if max_value is not None and num > max_value:
                    self._console.print(
                        Theme.format_status(f"Value must be at most {max_value}", "error")
                    )
                    continue
                
                return num
                
            except ValueError:
                self._console.print(
                    Theme.format_status("Please enter a valid number", "error")
                )
