import sys
from typing import Optional
from rich.console import Console
from rich.text import Text

from src.ui.styles.theme import Theme, Symbols


class PasswordInput:
    def __init__(self, console: Console):
        self._console = console

    def prompt(
        self,
        label: str = "Password",
        confirm: bool = False,
        min_length: Optional[int] = None,
        show_strength: bool = False,
    ) -> Optional[str]:
        prompt_text = Text()
        prompt_text.append(f"{Symbols.LOCK} ", style="primary")
        prompt_text.append(label, style="input.label")
        prompt_text.append(": ", style="input.prompt")

        while True:
            self._console.print(prompt_text, end="")
            
            password = self._get_hidden_input()
            
            if password is None:
                return None

            self._console.print()

            if not password:
                self._console.print(
                    Theme.format_status("Password cannot be empty", "error")
                )
                continue

            if min_length and len(password) < min_length:
                self._console.print(
                    Theme.format_status(
                        f"Password must be at least {min_length} characters",
                        "error"
                    )
                )
                continue

            if show_strength:
                strength = self._calculate_strength(password)
                self._display_strength(strength)

            if confirm:
                confirm_text = Text()
                confirm_text.append(f"{Symbols.LOCK} ", style="primary")
                confirm_text.append("Confirm password", style="input.label")
                confirm_text.append(": ", style="input.prompt")
                
                self._console.print(confirm_text, end="")
                
                confirm_password = self._get_hidden_input()
                
                if confirm_password is None:
                    return None

                self._console.print()

                if password != confirm_password:
                    self._console.print(
                        Theme.format_status("Passwords do not match", "error")
                    )
                    continue

            return password

    def prompt_app_password(
        self,
        label: str = "App Password",
    ) -> Optional[str]:
        prompt_text = Text()
        prompt_text.append(f"{Symbols.KEY} ", style="primary")
        prompt_text.append(label, style="input.label")
        prompt_text.append(" [16 characters]", style="input.placeholder")
        prompt_text.append(": ", style="input.prompt")

        while True:
            self._console.print(prompt_text, end="")
            
            password = self._get_hidden_input()
            
            if password is None:
                return None

            self._console.print()

            if not password:
                self._console.print(
                    Theme.format_status("App password cannot be empty", "error")
                )
                continue

            cleaned = password.replace(" ", "").replace("-", "")

            if len(cleaned) != 16:
                self._console.print(
                    Theme.format_status(
                        f"App password must be 16 characters (got {len(cleaned)})",
                        "error"
                    )
                )
                hint_text = Text()
                hint_text.append("  Hint: ", style="text.dim")
                hint_text.append(
                    "Copy the app password from Google without spaces",
                    style="text.muted"
                )
                self._console.print(hint_text)
                continue

            if not cleaned.isalnum():
                self._console.print(
                    Theme.format_status(
                        "App password should only contain letters and numbers",
                        "error"
                    )
                )
                continue

            return cleaned

    def _get_hidden_input(self) -> Optional[str]:
        try:
            if sys.platform == "win32":
                import msvcrt
                password = []
                while True:
                    char = msvcrt.getwch()
                    if char == "\r" or char == "\n":
                        break
                    elif char == "\x03":
                        raise KeyboardInterrupt
                    elif char == "\x08":
                        if password:
                            password.pop()
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                    else:
                        password.append(char)
                        sys.stdout.write("*")
                        sys.stdout.flush()
                return "".join(password)
            else:
                import termios
                import tty
                
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                
                try:
                    tty.setraw(fd)
                    password = []
                    
                    while True:
                        char = sys.stdin.read(1)
                        
                        if char == "\r" or char == "\n":
                            break
                        elif char == "\x03":
                            raise KeyboardInterrupt
                        elif char == "\x7f" or char == "\x08":
                            if password:
                                password.pop()
                                sys.stdout.write("\b \b")
                                sys.stdout.flush()
                        elif char == "\x04":
                            break
                        else:
                            password.append(char)
                            sys.stdout.write("*")
                            sys.stdout.flush()
                    
                    return "".join(password)
                    
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    
        except (KeyboardInterrupt, EOFError):
            self._console.print()
            return None
        except Exception:
            try:
                import getpass
                return getpass.getpass("")
            except (KeyboardInterrupt, EOFError):
                self._console.print()
                return None

    def _calculate_strength(self, password: str) -> int:
        score = 0
        
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        
        if any(c.islower() for c in password):
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        
        return min(score, 5)

    def _display_strength(self, strength: int) -> None:
        labels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
        colors = ["error", "error", "warning", "warning", "success", "success"]
        
        label = labels[strength]
        color = colors[strength]
        
        bar = "█" * strength + "░" * (5 - strength)
        
        strength_text = Text()
        strength_text.append("  Strength: ", style="text.dim")
        strength_text.append(bar, style=f"status.{color}")
        strength_text.append(f" {label}", style=f"status.{color}")
        
        self._console.print(strength_text)
