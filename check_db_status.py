"""Check database connection status."""
from app.config import Config
from app.utils.database import get_db_connection
import sys

def check_database_status():
    """Check and display database connection status."""
    config = Config()
    
    print("=" * 60)
    print("DATABASE CONFIGURATION STATUS")
    print("=" * 60)
    print(f"Host:        {config.DB_HOST}")
    print(f"Database:    {config.DB_NAME}")
    print(f"User:        {config.DB_USER}")
    print(f"Password:    {'*' * len(config.DB_PASSWORD) if config.DB_PASSWORD else 'Not set'}")
    print(f"Password:    {config.DB_PASSWORD[:3]}...{config.DB_PASSWORD[-3:] if len(config.DB_PASSWORD) > 6 else '***'}")
    print(f"Port:        {config.DB_PORT}")
    print()
    
    print("Attempting to connect...")
    try:
        conn = get_db_connection(config)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()
        print(f"✓ Connected successfully!")
        print(f"✓ Current database: {current_db[0] if current_db else 'None'}")
        
        # List tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"✓ Found {len(tables)} table(s):")
        for table in tables[:10]:  # Show first 10
            print(f"  - {table[0]}")
        if len(tables) > 10:
            print(f"  ... and {len(tables) - 10} more")
        
        # Check for key tables
        key_tables = ['users', 'txn_registry', 'excel_uploads', 'error_logs']
        print("\nKey tables status:")
        for table in key_tables:
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            exists = cursor.fetchone()
            status = "[OK] EXISTS" if exists else "[X] MISSING"
            print(f"  {status}: {table}")
        
        cursor.close()
        conn.close()
        print("\n" + "=" * 60)
        print("STATUS: Database is READY")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n[X] Connection FAILED!")
        print(f"Error: {type(e).__name__}: {str(e)}")
        print("\n" + "=" * 60)
        print("TROUBLESHOOTING:")
        print("=" * 60)
        print("1. Check if MySQL/MariaDB is running")
        print("2. Verify the password in app/config.py")
        print("3. Ensure the database 'crud' exists")
        print("4. Check user permissions")
        print("\nTo fix:")
        print("- Update DB_PASSWORD in app/config.py")
        print("- Or set environment variable: DB_PASSWORD=your_password")
        print("- Run crud.sql to create database and tables")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = check_database_status()
    sys.exit(0 if success else 1)

