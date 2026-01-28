import time
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error, pooling
from src.config import settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    _instance = None
    _pool = None
    _stats = {
        "connections_created": 0,
        "connections_failed": 0,
        "queries_executed": 0,
        "queries_failed": 0,
        "reconnections": 0,
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config = self._build_config()
        self._validate_config()
        self._create_pool()
        self._initialized = True

    def _build_config(self) -> Dict[str, Any]:
        return {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password,
            "charset": settings.database.charset,
            "collation": settings.database.collation,
            "autocommit": False,
            "raise_on_warnings": True,
            "get_warnings": True,
            "connection_timeout": settings.database.connection_timeout,
            "use_pure": True,
        }

    def _validate_config(self) -> None:
        if not settings.validate_database_config():
            raise ValueError("Missing required database configuration")

    def _create_pool(self) -> None:
        try:
            self._pool = pooling.MySQLConnectionPool(
                pool_name="mailbox_pool",
                pool_size=settings.database.pool_size,
                pool_reset_session=True,
                **self._config
            )
        except Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    def get_connection(self, max_retries: int = 3, retry_delay: int = 2):
        for attempt in range(1, max_retries + 1):
            try:
                connection = self._pool.get_connection()

                if connection.is_connected():
                    if not self._is_connection_healthy(connection):
                        connection.reconnect(attempts=3, delay=1)
                        self._stats["reconnections"] += 1

                    self._stats["connections_created"] += 1
                    return connection
                else:
                    connection.reconnect(attempts=3, delay=1)
                    self._stats["reconnections"] += 1
                    return connection

            except Error as e:
                self._stats["connections_failed"] += 1

                if attempt < max_retries:
                    delay = retry_delay * (2 ** (attempt - 1))
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to get connection after {max_retries} attempts: {e}")
                    raise

        raise Error("Failed to establish database connection")

    def _is_connection_healthy(self, connection) -> bool:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Error:
            return False

    @contextmanager
    def get_cursor(self, dictionary: bool = False, buffered: bool = True):
        connection = None
        cursor = None

        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=dictionary, buffered=buffered)
            yield cursor
            connection.commit()
            self._stats["queries_executed"] += 1

        except Error as e:
            if connection:
                connection.rollback()
            self._stats["queries_failed"] += 1
            logger.error(f"Database operation failed: {e}")
            raise

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def execute_query(
        self, query: str, params: tuple = None, fetch: bool = True
    ) -> Optional[List]:
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            return None

    def execute_many(self, query: str, data: List[tuple]) -> int:
        with self.get_cursor() as cursor:
            cursor.executemany(query, data)
            return cursor.rowcount

    def test_connection(self) -> bool:
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result and result[0] == 1
        except Error:
            return False

    def get_stats(self) -> Dict[str, int]:
        return self._stats.copy()

    def reset_stats(self) -> None:
        for key in self._stats:
            self._stats[key] = 0


_db_connection = None


def _get_db_instance() -> DatabaseConnection:
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection


def get_connection():
    return _get_db_instance().get_connection()


def get_cursor(dictionary: bool = False, buffered: bool = True):
    return _get_db_instance().get_cursor(dictionary=dictionary, buffered=buffered)


def execute_query(query: str, params: tuple = None, fetch: bool = True):
    return _get_db_instance().execute_query(query, params, fetch)


def execute_many(query: str, data: List[tuple]):
    return _get_db_instance().execute_many(query, data)


def test_connection() -> bool:
    return _get_db_instance().test_connection()


def get_stats() -> Dict[str, int]:
    return _get_db_instance().get_stats()
