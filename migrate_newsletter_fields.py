#!/usr/bin/env python3
"""
One-time migration script to add newsletter_type and verbosity_level fields.
Run this once to update existing databases.
"""
import asyncio
import sqlite3
from pathlib import Path

async def migrate_newsletter_fields():
    """Add newsletter_type and verbosity_level columns to existing newsletters table."""
    db_path = Path("data/app.db")

    if not db_path.exists():
        print("No database found at data/app.db - nothing to migrate")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(newsletters)")
        columns = [row[1] for row in cursor.fetchall()]

        if "newsletter_type" not in columns:
            print("Adding newsletter_type column...")
            cursor.execute("ALTER TABLE newsletters ADD COLUMN newsletter_type VARCHAR(50) DEFAULT 'general_business'")
        else:
            print("newsletter_type column already exists")

        if "verbosity_level" not in columns:
            print("Adding verbosity_level column...")
            cursor.execute("ALTER TABLE newsletters ADD COLUMN verbosity_level VARCHAR(20) DEFAULT 'medium'")
        else:
            print("verbosity_level column already exists")

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_newsletter_fields())