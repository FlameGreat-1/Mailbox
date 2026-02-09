import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    charset: str = "utf8mb4"
    collation: str = "utf8mb4_unicode_ci"
    pool_size: int = 5
    connection_timeout: int = 30


@dataclass(frozen=True)
class GoogleConfig:
    client_id: Optional[str]
    client_secret: Optional[str]
    redirect_uri: str
    callback_port: int
    scopes: tuple


@dataclass(frozen=True)
class EmailConfig:
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    connection_timeout: int = 30


@dataclass(frozen=True)
class ZohoConfig:
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    connection_timeout: int = 30


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    version: str
    encryption_key: Optional[str]


class Settings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.database = DatabaseConfig(
            host=os.getenv("DB_HOST", ""),
            port=int(os.getenv("DB_PORT", "3306")),
            name=os.getenv("DB_NAME", ""),
            user=os.getenv("DB_USER", ""),
            password=os.getenv("DB_PASSWORD", ""),
        )

        self.google = GoogleConfig(
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/callback"),
            callback_port=int(os.getenv("OAUTH_CALLBACK_PORT", "8080")),
            scopes=(
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/calendar.readonly",
            ),
        )

        self.email = EmailConfig(
            imap_host="imap.gmail.com",
            imap_port=993,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
        )

        self.zoho = ZohoConfig(
            imap_host="imap.zoho.com",
            imap_port=993,
            smtp_host="smtp.zoho.com",
            smtp_port=465,
        )

        self.app = AppConfig(
            app_name="Mailbox",
            version="1.0.0",
            encryption_key=os.getenv("ENCRYPTION_KEY"),
        )

        self._initialized = True

    def validate_database_config(self) -> bool:
        required = [
            self.database.host,
            self.database.name,
            self.database.user,
            self.database.password,
        ]
        return all(required)

    def validate_google_oauth_config(self) -> bool:
        return bool(self.google.client_id and self.google.client_secret)

    def validate_encryption_config(self) -> bool:
        return bool(self.app.encryption_key)


settings = Settings()
