import mysql.connector
from src.config import settings

# Connect to database
conn = mysql.connector.connect(
    host=settings.database.host,
    port=settings.database.port,
    user=settings.database.user,
    password=settings.database.password,
    database=settings.database.name,
)

cursor = conn.cursor()

# Run migration
sql = """
ALTER TABLE credentials 
MODIFY COLUMN auth_type ENUM('oauth', 'app_password', 'zoho') NOT NULL
"""

try:
    cursor.execute(sql)
    conn.commit()
    print("✅ Database migration successful!")
    print("   Added 'zoho' to auth_type ENUM")
except Exception as e:
    print(f"❌ Migration failed: {e}")
finally:
    cursor.close()
    conn.close()

