from typing import Optional
from datetime import datetime
from src.database.connection import get_cursor
from src.database.models import Credential, AuthType


class CredentialsRepository:
    TABLE_NAME = "credentials"

    @classmethod
    def create_table(cls) -> None:
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL UNIQUE,
            auth_type ENUM('oauth', 'app_password', 'zoho') NOT NULL,
            encrypted_token TEXT NOT NULL,
            access_token TEXT,
            token_expiry DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_email (user_email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with get_cursor() as cursor:
            cursor.execute(query)

    @classmethod
    def save(cls, credential: Credential) -> Credential:
        if credential.id:
            return cls._update(credential)
        return cls._insert(credential)

    @classmethod
    def _insert(cls, credential: Credential) -> Credential:
        query = f"""
        INSERT INTO {cls.TABLE_NAME} 
        (user_email, auth_type, encrypted_token, access_token, token_expiry)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            credential.user_email,
            credential.auth_type.value,
            credential.encrypted_token,
            credential.access_token,
            credential.token_expiry,
        )

        with get_cursor() as cursor:
            cursor.execute(query, params)
            credential.id = cursor.lastrowid

        return credential

    @classmethod
    def _update(cls, credential: Credential) -> Credential:
        query = f"""
        UPDATE {cls.TABLE_NAME}
        SET auth_type = %s, encrypted_token = %s, access_token = %s, token_expiry = %s
        WHERE id = %s
        """
        params = (
            credential.auth_type.value,
            credential.encrypted_token,
            credential.access_token,
            credential.token_expiry,
            credential.id,
        )

        with get_cursor() as cursor:
            cursor.execute(query, params)

        return credential

    @classmethod
    def find_by_email(cls, user_email: str) -> Optional[Credential]:
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE user_email = %s"

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email,))
            row = cursor.fetchone()

            if row:
                return Credential.from_db_row(row)
            return None

    @classmethod
    def find_first(cls) -> Optional[Credential]:
        query = f"SELECT * FROM {cls.TABLE_NAME} ORDER BY updated_at DESC LIMIT 1"

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query)
            row = cursor.fetchone()

            if row:
                return Credential.from_db_row(row)
            return None

    @classmethod
    def exists(cls, user_email: str) -> bool:
        query = f"SELECT 1 FROM {cls.TABLE_NAME} WHERE user_email = %s LIMIT 1"

        with get_cursor() as cursor:
            cursor.execute(query, (user_email,))
            return cursor.fetchone() is not None

    @classmethod
    def update_tokens(
        cls,
        user_email: str,
        encrypted_token: str,
        access_token: Optional[str] = None,
        token_expiry: Optional[datetime] = None,
    ) -> bool:
        query = f"""
        UPDATE {cls.TABLE_NAME}
        SET encrypted_token = %s, access_token = %s, token_expiry = %s
        WHERE user_email = %s
        """
        params = (encrypted_token, access_token, token_expiry, user_email)

        with get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount > 0

    @classmethod
    def delete_by_email(cls, user_email: str) -> bool:
        query = f"DELETE FROM {cls.TABLE_NAME} WHERE user_email = %s"

        with get_cursor() as cursor:
            cursor.execute(query, (user_email,))
            return cursor.rowcount > 0

    @classmethod
    def upsert(cls, credential: Credential) -> Credential:
        existing = cls.find_by_email(credential.user_email)

        if existing:
            credential.id = existing.id
            return cls._update(credential)

        return cls._insert(credential)
