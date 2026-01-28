import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database.connection import test_connection, get_stats, get_cursor


def run_connection_test() -> bool:
    print("\n" + "=" * 60)
    print("  MAILBOX CONNECTION TEST")
    print("=" * 60 + "\n")

    print("[1/3] Validating configuration...")
    print(f"  Host: {settings.database.host}")
    print(f"  Port: {settings.database.port}")
    print(f"  Database: {settings.database.name}")
    print(f"  User: {settings.database.user}")

    if not settings.validate_database_config():
        print("\n✗ Invalid database configuration")
        return False
    print("✓ Configuration valid\n")

    print("[2/3] Testing database connection...")
    if not test_connection():
        print("✗ Connection test failed")
        return False
    print("✓ Connection test passed\n")

    print("[3/3] Fetching server information...")
    try:
        with get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT VERSION() as version")
            row = cursor.fetchone()
            print(f"  MySQL Version: {row['version']}")

            cursor.execute("SELECT DATABASE() as db")
            row = cursor.fetchone()
            print(f"  Current Database: {row['db']}")

            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"  Tables: {len(tables)}")
            for table in tables:
                table_name = list(table.values())[0]
                print(f"    - {table_name}")

    except Exception as e:
        print(f"✗ Failed to fetch server info: {e}")
        return False

    print("\n" + "-" * 60)
    print("Connection Statistics:")
    stats = get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60 + "\n")

    return True


if __name__ == "__main__":
    success = run_connection_test()
    sys.exit(0 if success else 1)
