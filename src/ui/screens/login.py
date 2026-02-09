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

        return self._show_auth_options()

    def _show_auth_options(self) -> Tuple[bool, Optional[str]]:
        self._console.print()
        
        info_panel = Panel(
            Text.from_markup(
                f"{Symbols.INFO} [text]Choose your authentication method:[/text]\n\n"
                f"[text.dim]• [primary]Sign in with Google[/primary] - Secure OAuth, includes Gmail & Calendar[/text.dim]\n"
                f"[text.dim]• [primary]Zoho Mail[/primary] - Email + password for Zoho accounts[/text.dim]"
            ),
            border_style="primary",
            padding=(1, 2),
        )
        self._console.print(info_panel)

        self._console.print()

        choices = [
            "Sign in with Google",
            "Zoho Mail"
        ]
        
        if not self._auth_manager.has_oauth_client_secret():
            choices[0] = "Sign in with Google (Not configured - client_secret.json missing)"

        choice = self._text_input.prompt_choice(
            "Select authentication method",
            choices,
            default=1,
        )

        if choice is None:
            return False, None

        if choice == 1:
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
            
            return self._login_with_google()
        elif choice == 2:
            return self._login_with_zoho()

        return False, None

    def _login_with_google(self) -> Tuple[bool, Optional[str]]:
        self._clear_screen()
        self._header.render(
            title=settings.app.app_name,
            subtitle="Sign in with Google",
        )

        self._console.print()
        
        info_panel = Panel(
            Text.from_markup(
                f"{Symbols.INFO} [text]Google Sign-In Process:[/text]\n\n"
                f"[text.dim]1. Your browser will open automatically[/text.dim]\n"
                f"[text.dim]2. Sign in with your Google account[/text.dim]\n"
                f"[text.dim]3. Grant permissions for Gmail and Calendar[/text.dim]\n"
                f"[text.dim]4. You'll be redirected back automatically[/text.dim]"
            ),
            border_style="info",
            padding=(1, 2),
        )
        self._console.print(info_panel)

        self._console.print()
        
        proceed = self._text_input.prompt_confirm(
            "Ready to sign in with Google?",
            default=True,
        )

        if not proceed:
            return False, None

        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Starting OAuth authentication...", style="text")
        self._console.print(status_text)
        
        self._console.print()
        self._console.print(Text.from_markup(
            "[text.dim]→ Opening browser for Google sign-in...[/text.dim]"
        ))
        self._console.print(Text.from_markup(
            "[text.dim]→ Waiting for authorization...[/text.dim]"
        ))
        self._console.print()
        
        waiting_panel = Panel(
            Text.from_markup(
                f"[warning]⏳ Please complete the sign-in process in your browser[/warning]\n\n"
                f"[text.dim]This may take a few moments...[/text.dim]"
            ),
            border_style="warning",
            padding=(1, 2),
        )
        self._console.print(waiting_panel)

        success, message = self._auth_manager.authenticate_with_oauth()

        self._console.print()

        if success:
            self._console.print(Text("✓ Sign-in successful!", style="success"))
            self._console.print()
            
            self._console.print(Text.from_markup(
                f"[text.dim]Your account has been connected:[/text.dim]\n"
                f"[primary]• Gmail access enabled[/primary]\n"
                f"[primary]• Calendar access enabled[/primary]\n"
                f"[text.dim]Your credentials are securely encrypted and stored.[/text.dim]"
            ))
            
            input("\nPress Enter to continue...")
            return True, self._auth_manager.current_email
        else:
            self._console.print(Theme.format_status(f"✗ {message}", "error"))
            self._console.print()
            
            if "timeout" in message.lower():
                self._console.print(Text.from_markup(
                    "[text.dim]The sign-in process timed out. This can happen if:[/text.dim]\n"
                    "[text.dim]• You didn't complete the sign-in within 5 minutes[/text.dim]\n"
                    "[text.dim]• The browser window was closed[/text.dim]\n"
                    "[text.dim]• Network connectivity issues[/text.dim]"
                ))
            elif "cancelled" in message.lower():
                self._console.print(Text.from_markup(
                    "[text.dim]Sign-in was cancelled. No changes were made.[/text.dim]"
                ))
            
            self._console.print()
            retry = self._text_input.prompt_confirm("Would you like to try again?", default=True)
            
            if retry:
                return self._login_with_google()
            
            return False, None

    def _login_with_zoho(self) -> Tuple[bool, Optional[str]]:
        self._clear_screen()
        self._header.render(
            title=settings.app.app_name,
            subtitle="Zoho Mail Login",
        )

        self._console.print()
        
        info_panel = Panel(
            Text.from_markup(
                f"{Symbols.INFO} [text]Zoho Mail Authentication:[/text]\n\n"
                f"[text.dim]• Use your regular Zoho email and password[/text.dim]\n"
                f"[text.dim]• Email access only (no calendar support)[/text.dim]\n"
                f"[text.dim]• Works with any Zoho Mail account[/text.dim]\n\n"
                f"[warning]Note: Your password will be encrypted and stored securely[/warning]"
            ),
            border_style="info",
            padding=(1, 2),
        )
        self._console.print(info_panel)

        self._console.print()

        email = self._text_input.prompt_email("Zoho Email Address")
        
        if not email:
            return False, None

        if not email.endswith("@zoho.com") and not email.endswith("@zohomail.com"):
            self._console.print()
            proceed = self._text_input.prompt_confirm(
                f"'{email}' doesn't appear to be a Zoho address. Continue anyway?",
                default=True,
            )
            if not proceed:
                return self._login_with_zoho()

        self._console.print()
        
        password = self._password_input.prompt("Zoho Password")
        
        if not password:
            return False, None

        self._console.print()
        
        status_text = Text()
        status_text.append(f"{Symbols.LOADING} ", style="info")
        status_text.append("Authenticating with Zoho Mail...", style="text")
        self._console.print(status_text)

        success, message = self._auth_manager.authenticate_with_zoho(email, password)

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
                return self._login_with_zoho()
            
            return False, None

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")
