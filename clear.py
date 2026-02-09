import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import get_cursor

def clear_mailbox_data():
    """
    Clear all data from Mailbox app tables without deleting the tables.
    Only affects: credentials, email_messages, calendar_events
    """
    
    tables_to_clear = [
        "credentials",
        "email_messages", 
        "calendar_events"
    ]
    
    print("=" * 60)
    print("MAILBOX DATABASE CLEANUP")
    print("=" * 60)
    print("\nThis will DELETE ALL DATA from the following tables:")
    for table in tables_to_clear:
        print(f"  - {table}")
    print("\nTable structures will be preserved.")
    print("=" * 60)
    
    confirm = input("\nType 'YES' to confirm deletion: ")
    
    if confirm != "YES":
        print("\n❌ Operation cancelled.")
        return
    
    try:
        with get_cursor() as cursor:
            # Disable foreign key checks temporarily
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            for table in tables_to_clear:
                # Check if table exists
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                if cursor.fetchone():
                    cursor.execute(f"TRUNCATE TABLE {table}")
                    print(f"✅ Cleared table: {table}")
                else:
                    print(f"⚠️  Table not found: {table}")
            
            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        print("\n" + "=" * 60)
        print("✅ DATABASE CLEANUP COMPLETE")
        print("=" * 60)
        print("\nAll Mailbox data has been deleted.")
        print("Tables are ready for fresh data.")
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    clear_mailbox_data()
