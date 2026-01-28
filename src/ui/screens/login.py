import os
from typing import Optional, Tuple
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from src.config import settings
from src.auth.manager import AuthManager, AuthMethod, get_auth_manager
from src.ui.styles.theme import Theme, Symbols
from src.ui.components.header import Header
from src.ui.components.footer import Footer
from src.ui.components.inputs.text import TextInput
from src.ui.components.inputs.password import PasswordInput


class LoginScreen:
    def __init__(self, console: Console, auth_manager: Optional[AuthManager] = None):
        self._console = console
        self._auth_manager = auth_manager or get_auth_manager()
        self._header = Header(console)
        self._footer = Footer(console)
        self._text_input = TextInput(console)
        self._password_input = PasswordInput(console)

    def show(self) -> Tuple[bool, Optional[str]]:
        self._clear_screen()
        self._header.render(
            title=settings.app.app_name,
            subtitle="Welcome",
        )

        if self._auth_manager.has_stored_credentials():
            return self._auto_login()

        return self._show_auth_options()

    def _auto_login(self) -> Tuple[bool, Optional[str]]:
        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Found stored credentials. Authenticating...", style="text")
        self._console.print(status_text)

        success, message = self._auth_manager.auto_authenticate()

        self._console.print()

        if success:
            self._console.print(Theme.format_status(message, "success"))
            return True, self._auth_manager.current_email
        else:
            self._console.print(Theme.format_status(message, "error"))
            self._console.print()
            
            retry = self._text_input.prompt_confirm(
                "Would you like to login with new credentials?",
                default=True,
            )
            
            if retry:
                return self._show_auth_options()
            
            return False, None

    def _show_auth_options(self) -> Tuple[bool, Optional[str]]:
        self._console.print()
        
        info_panel = Panel(
            Text.from_markup(
                f"{Symbols.INFO} [text]Choose your authentication method:[/text]\n\n"
                f"[text.dim]• [primary]App Password[/primary] - Simple setup, works entirely in terminal[/text.dim]\n"
                f"[text.dim]• [primary]OAuth 2.0[/primary] - More secure, requires browser for initial setup[/text.dim]"
            ),
            border_style="primary",
            padding=(1, 2),
        )
        self._console.print(info_panel)

        self._console.print()

        choices = ["App Password (Recommended for CLI)", "OAuth 2.0 (Google Sign-In)"]
        
        if not self._auth_manager.has_oauth_client_secret():
            choices[1] = "OAuth 2.0 (Not configured - client_secret.json missing)"

        choice = self._text_input.prompt_choice(
            "Select authentication method",
            choices,
            default=1,
        )

        if choice is None:
            return False, None

        if choice == 1:
            return self._login_with_app_password()
        elif choice == 2:
            if not self._auth_manager.has_oauth_client_secret():
                self._console.print()
                self._console.print(Theme.format_status(
                    "OAuth not configured. Please add client_secret.json to credentials folder.",
                    "error"
                ))
                self._console.print()
                
                hint_text = Text()
                hint_text.append("  To set up OAuth:\n", style="text.dim")
                hint_text.append("  1. Go to Google Cloud Console\n", style="text.muted")
                hint_text.append("  2. Create OAuth 2.0 credentials\n", style="text.muted")
                hint_text.append("  3. Download and save as credentials/client_secret.json\n", style="text.muted")
                self._console.print(hint_text)
                
                input("\nPress Enter to continue...")
                return self._show_auth_options()
            
            return self._login_with_oauth()

        return False, None

    def _login_with_app_password(self) -> Tuple[bool, Optional[str]]:
        self._clear_screen()
        self._header.render(
            title=settings.app.app_name,
            subtitle="App Password Login",
        )

        self._console.print()
        
        info_panel = Panel(
            Text.from_markup(
                f"{Symbols.INFO} [text]To get an App Password:[/text]\n\n"
                f"[text.dim]1. Go to [link]https://myaccount.google.com/apppasswords[/link][/text.dim]\n"
                f"[text.dim]2. Select 'Mail' and your device[/text.dim]\n"
                f"[text.dim]3. Copy the 16-character password[/text.dim]\n\n"
                f"[warning]Note: 2-Factor Authentication must be enabled[/warning]"
            ),
            border_style="info",
            padding=(1, 2),
        )
        self._console.print(info_panel)

        self._console.print()

        email = self._text_input.prompt_email("Gmail Address")
        
        if not email:
            return False, None

        if not email.endswith("@gmail.com") and not email.endswith("@googlemail.com"):
            self._console.print()
            proceed = self._text_input.prompt_confirm(
                f"'{email}' doesn't appear to be a Gmail address. Continue anyway?",
                default=False,
            )
            if not proceed:
                return self._login_with_app_password()

        self._console.print()
        
        app_password = self._password_input.prompt_app_password()
        
        if not app_password:
            return False, None

        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Authenticating with Gmail...", style="text")
        self._console.print(status_text)

        success, message = self._auth_manager.authenticate_with_app_password(email, app_password)

        self._console.print()

        if success:
            self._console.print(Theme.format_status("Login successful!", "success"))
            self._console.print()
            
            self._console.print(Text.from_markup(
                f"[text.dim]Your credentials have been securely encrypted and stored.[/text.dim]"
            ))
            
            input("\nPress Enter to continue...")
            return True, email
        else:
            self._console.print(Theme.format_status(message, "error"))
            self._console.print()
            
            retry = self._text_input.prompt_confirm("Would you like to try again?", default=True)
            
            if retry:
                return self._login_with_app_password()
            
            return False, None

    def _login_with_oauth(self) -> Tuple[bool, Optional[str]]:
        self._clear_screen()
        self._header.render(
            title=settings.app.app_name,
            subtitle="OAuth 2.0 Login",
        )

        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Generating authorization URL...", style="text")
        self._console.print(status_text)

        auth_url, message = self._auth_manager.get_oauth_authorization_url()

        if not auth_url:
            self._console.print()
            self._console.print(Theme.format_status(message, "error"))
            input("\nPress Enter to continue...")
            return self._show_auth_options()

        self._console.print()
        
        info_panel = Panel(
            Text.from_markup(
                f"{Symbols.INFO} [text]Complete the following steps:[/text]\n\n"
                f"[text.dim]1. Open the URL below in your browser[/text.dim]\n"
                f"[text.dim]2. Sign in with your Google account[/text.dim]\n"
                f"[text.dim]3. Grant the requested permissions[/text.dim]\n"
                f"[text.dim]4. Copy the authorization code[/text.dim]\n"
                f"[text.dim]5. Paste it below[/text.dim]"
            ),
            border_style="info",
            padding=(1, 2),
        )
        self._console.print(info_panel)

        self._console.print()
        
        url_text = Text()
        url_text.append("Authorization URL:\n", style="text.dim")
        url_text.append(auth_url, style="link")
        self._console.print(url_text)

        self._console.print()
        
        open_browser = self._text_input.prompt_confirm(
            "Would you like to open this URL in your browser?",
            default=True,
        )

        if open_browser:
            success, _ = self._auth_manager.open_oauth_in_browser()
            if success:
                self._console.print(Theme.format_status("Browser opened", "success"))
            else:
                self._console.print(Theme.format_status(
                    "Could not open browser. Please copy the URL manually.",
                    "warning"
                ))

        self._console.print()
        
        auth_code = self._text_input.prompt(
            "Authorization Code",
            required=True,
            placeholder="Paste the code from Google here",
        )

        if not auth_code:
            return False, None

        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Completing authentication...", style="text")
        self._console.print(status_text)

        success, message = self._auth_manager.authenticate_with_oauth_code(auth_code)

        self._console.print()

        if success:
            self._console.print(Theme.format_status(message, "success"))
            self._console.print()
            
            self._console.print(Text.from_markup(
                f"[text.dim]Your OAuth tokens have been securely encrypted and stored.[/text.dim]"
            ))
            
            input("\nPress Enter to continue...")
            return True, self._auth_manager.current_email
        else:
            self._console.print(Theme.format_status(message, "error"))
            self._console.print()
            
            retry = self._text_input.prompt_confirm("Would you like to try again?", default=True)
            
            if retry:
                return self._login_with_oauth()
            
            return False, None

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
