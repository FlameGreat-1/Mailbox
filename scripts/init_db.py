import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import test_connection
from src.database.repositories import (
    CredentialsRepository,
    EmailsRepository,
    CalendarRepository,
)


def init_database() -> bool:
    print("\n" + "=" * 60)
    print("  MAILBOX DATABASE INITIALIZATION")
    print("=" * 60 + "\n")

    print("[1/4] Testing database connection...")
    if not test_connection():
        print("✗ Database connection failed")
        return False
    print("✓ Database connection successful\n")

    print("[2/4] Creating credentials table...")
    try:
        CredentialsRepository.create_table()
        print("✓ Credentials table ready\n")
    except Exception as e:
        print(f"✗ Failed to create credentials table: {e}")
        return False

    print("[3/4] Creating email_messages table...")
    try:
        EmailsRepository.create_table()
        print("✓ Email messages table ready\n")
    except Exception as e:
        print(f"✗ Failed to create email_messages table: {e}")
        return False

    print("[4/4] Creating calendar_events table...")
    try:
        CalendarRepository.create_table()
        print("✓ Calendar events table ready\n")
    except Exception as e:
        print(f"✗ Failed to create calendar_events table: {e}")
        return False

    print("=" * 60)
    print("  DATABASE INITIALIZATION COMPLETE")
    print("=" * 60 + "\n")

    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
