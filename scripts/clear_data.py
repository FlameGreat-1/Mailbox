import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import get_cursor


def clear_mailbox_data():
    print("\n" + "=" * 60)
    print("  MAILBOX DATA CLEANUP")
    print("=" * 60 + "\n")

    tables = [
        "calendar_events",
        "email_messages",
        "credentials",
    ]

    print("This will DELETE all data from:")
    for table in tables:
        print(f"  - {table}")
    
    print("\nOther tables in your database will NOT be affected.\n")
    
    confirm = input("Type 'YES' to confirm: ").strip()
    
    if confirm != "YES":
        print("\n✗ Operation cancelled\n")
        return False

    print()

    for table in tables:
        try:
            with get_cursor() as cursor:
                cursor.execute(f"DELETE FROM {table}")
                deleted = cursor.rowcount
                print(f"✓ Cleared {table}: {deleted} rows deleted")
        except Exception as e:
            print(f"✗ Failed to clear {table}: {e}")
            return False

    print("\n" + "=" * 60)
    print("  CLEANUP COMPLETE")
    print("=" * 60 + "\n")

    return True


if __name__ == "__main__":
    success = clear_mailbox_data()
    sys.exit(0 if success else 1)
