import json
from typing import Optional, List
from datetime import datetime
from src.database.connection import get_cursor, execute_many
from src.database.models import Email


class EmailsRepository:
    TABLE_NAME = "email_messages"

    @classmethod
    def create_table(cls) -> None:
        query = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255),
            from_address VARCHAR(255) NOT NULL,
            from_name VARCHAR(255),
            to_addresses JSON,
            cc_addresses JSON,
            subject TEXT,
            body_text LONGTEXT,
            body_html LONGTEXT,
            date_received DATETIME,
            is_read BOOLEAN DEFAULT FALSE,
            labels JSON,
            has_attachments BOOLEAN DEFAULT FALSE,
            attachments_meta JSON,
            folder VARCHAR(50) DEFAULT 'inbox',
            synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_message (user_email, message_id),
            INDEX idx_user_email (user_email),
            INDEX idx_date_received (date_received),
            INDEX idx_folder (folder),
            INDEX idx_is_read (is_read),
            FULLTEXT INDEX ft_subject_body (subject, body_text)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with get_cursor() as cursor:
            cursor.execute(query)

    @classmethod
    def save(cls, email: Email) -> Email:
        if email.id:
            return cls._update(email)
        return cls._insert(email)

    @classmethod
    def _insert(cls, email: Email) -> Email:
        query = f"""
        INSERT INTO {cls.TABLE_NAME} 
        (user_email, message_id, thread_id, from_address, from_name, to_addresses,
         cc_addresses, subject, body_text, body_html, date_received, is_read,
         labels, has_attachments, attachments_meta, folder, synced_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        data = email.to_dict()
        params = (
            data["user_email"],
            data["message_id"],
            data["thread_id"],
            data["from_address"],
            data["from_name"],
            data["to_addresses"],
            data["cc_addresses"],
            data["subject"],
            data["body_text"],
            data["body_html"],
            data["date_received"],
            data["is_read"],
            data["labels"],
            data["has_attachments"],
            data["attachments_meta"],
            data["folder"],
            datetime.now(),
        )

        with get_cursor() as cursor:
            cursor.execute(query, params)
            email.id = cursor.lastrowid

        return email

    @classmethod
    def _update(cls, email: Email) -> Email:
        query = f"""
        UPDATE {cls.TABLE_NAME}
        SET thread_id = %s, from_address = %s, from_name = %s, to_addresses = %s,
            cc_addresses = %s, subject = %s, body_text = %s, body_html = %s,
            date_received = %s, is_read = %s, labels = %s, has_attachments = %s,
            attachments_meta = %s, folder = %s, synced_at = %s
        WHERE id = %s
        """
        data = email.to_dict()
        params = (
            data["thread_id"],
            data["from_address"],
            data["from_name"],
            data["to_addresses"],
            data["cc_addresses"],
            data["subject"],
            data["body_text"],
            data["body_html"],
            data["date_received"],
            data["is_read"],
            data["labels"],
            data["has_attachments"],
            data["attachments_meta"],
            data["folder"],
            datetime.now(),
            email.id,
        )

        with get_cursor() as cursor:
            cursor.execute(query, params)

        return email

    @classmethod
    def bulk_insert(cls, emails: List[Email]) -> int:
        if not emails:
            return 0

        query = f"""
        INSERT INTO {cls.TABLE_NAME} 
        (user_email, message_id, thread_id, from_address, from_name, to_addresses,
         cc_addresses, subject, body_text, body_html, date_received, is_read,
         labels, has_attachments, attachments_meta, folder, synced_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            thread_id = VALUES(thread_id),
            is_read = VALUES(is_read),
            labels = VALUES(labels),
            synced_at = VALUES(synced_at)
        """
        now = datetime.now()
        data = []
        for email in emails:
            d = email.to_dict()
            data.append((
                d["user_email"],
                d["message_id"],
                d["thread_id"],
                d["from_address"],
                d["from_name"],
                d["to_addresses"],
                d["cc_addresses"],
                d["subject"],
                d["body_text"],
                d["body_html"],
                d["date_received"],
                d["is_read"],
                d["labels"],
                d["has_attachments"],
                d["attachments_meta"],
                d["folder"],
                now,
            ))

        return execute_many(query, data)

    @classmethod
    def find_by_id(cls, email_id: int) -> Optional[Email]:
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE id = %s"

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (email_id,))
            row = cursor.fetchone()

            if row:
                return Email.from_db_row(row)
            return None

    @classmethod
    def find_by_message_id(cls, user_email: str, message_id: str) -> Optional[Email]:
        query = f"SELECT * FROM {cls.TABLE_NAME} WHERE user_email = %s AND message_id = %s"

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email, message_id))
            row = cursor.fetchone()

            if row:
                return Email.from_db_row(row)
            return None

    @classmethod
    def find_by_user(
        cls,
        user_email: str,
        folder: str = "inbox",
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> List[Email]:
        query = f"""
        SELECT * FROM {cls.TABLE_NAME}
        WHERE user_email = %s AND folder = %s
        """
        params = [user_email, folder]

        if unread_only:
            query += " AND is_read = FALSE"

        query += " ORDER BY date_received DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            return [Email.from_db_row(row) for row in rows]

    @classmethod
    def search(cls, user_email: str, search_term: str, limit: int = 50) -> List[Email]:
        query = f"""
        SELECT * FROM {cls.TABLE_NAME}
        WHERE user_email = %s 
        AND MATCH(subject, body_text) AGAINST(%s IN NATURAL LANGUAGE MODE)
        ORDER BY date_received DESC
        LIMIT %s
        """

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email, search_term, limit))
            rows = cursor.fetchall()

            return [Email.from_db_row(row) for row in rows]

    @classmethod
    def mark_as_read(cls, email_id: int) -> bool:
        query = f"UPDATE {cls.TABLE_NAME} SET is_read = TRUE WHERE id = %s"

        with get_cursor() as cursor:
            cursor.execute(query, (email_id,))
            return cursor.rowcount > 0

    @classmethod
    def mark_as_unread(cls, email_id: int) -> bool:
        query = f"UPDATE {cls.TABLE_NAME} SET is_read = FALSE WHERE id = %s"

        with get_cursor() as cursor:
            cursor.execute(query, (email_id,))
            return cursor.rowcount > 0

    @classmethod
    def get_unread_count(cls, user_email: str, folder: str = "inbox") -> int:
        query = f"""
        SELECT COUNT(*) as count FROM {cls.TABLE_NAME}
        WHERE user_email = %s AND folder = %s AND is_read = FALSE
        """

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email, folder))
            row = cursor.fetchone()
            return row["count"] if row else 0

    @classmethod
    def get_total_count(cls, user_email: str, folder: str = "inbox") -> int:
        query = f"""
        SELECT COUNT(*) as count FROM {cls.TABLE_NAME}
        WHERE user_email = %s AND folder = %s
        """

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email, folder))
            row = cursor.fetchone()
            return row["count"] if row else 0

    @classmethod
    def get_latest_message_date(cls, user_email: str) -> Optional[datetime]:
        query = f"""
        SELECT MAX(date_received) as latest FROM {cls.TABLE_NAME}
        WHERE user_email = %s
        """

        with get_cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_email,))
            row = cursor.fetchone()
            return row["latest"] if row else None

    @classmethod
    def message_exists(cls, user_email: str, message_id: str) -> bool:
        query = f"""
        SELECT 1 FROM {cls.TABLE_NAME}
        WHERE user_email = %s AND message_id = %s LIMIT 1
        """

        with get_cursor() as cursor:
            cursor.execute(query, (user_email, message_id))
            return cursor.fetchone() is not None

    @classmethod
    def delete_by_user(cls, user_email: str) -> int:
        query = f"DELETE FROM {cls.TABLE_NAME} WHERE user_email = %s"

        with get_cursor() as cursor:
            cursor.execute(query, (user_email,))
            return cursor.rowcount
