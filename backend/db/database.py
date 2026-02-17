"""
Database connection and session management
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from db.models import Base
from config import settings


# Database path from settings
DB_PATH = Path(settings.database_path)
DB_DIR = DB_PATH.parent

# Create data directory if it doesn't exist
DB_DIR.mkdir(parents=True, exist_ok=True)

# SQLite connection string
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
# For SQLite, we use StaticPool and check_same_thread=False for async support
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_db():
    """Add new columns to existing tables (SQLite ALTER TABLE).

    SQLAlchemy create_all does NOT add columns to existing tables.
    This function adds missing columns idempotently.
    """
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # --- Migrate problems table columns ---
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='problems'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(problems)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        migrations = [
            ("card_status", "VARCHAR(20) NOT NULL DEFAULT 'new'"),
            ("first_viewed_at", "DATETIME"),
            ("last_viewed_at", "DATETIME"),
            ("archived_at", "DATETIME"),
            ("verified_at", "DATETIME"),
            ("view_count", "INTEGER NOT NULL DEFAULT 0"),
            ("is_starred", "BOOLEAN NOT NULL DEFAULT 0"),
            ("user_notes", "TEXT"),
            ("user_tags", "JSON"),
            ("audience_type", "VARCHAR(20) NOT NULL DEFAULT 'unknown'"),
        ]

        added = 0
        for col_name, col_type in migrations:
            if col_name not in existing_columns:
                cursor.execute(f"ALTER TABLE problems ADD COLUMN {col_name} {col_type}")
                print(f"  Migration: added column problems.{col_name}")
                added += 1

        if added:
            print(f"  Migration complete: {added} columns added")

        # Backfill audience_type for legacy records with unknown values
        if "audience_type" in existing_columns or any(m[0] == "audience_type" for m in migrations):
            cursor.execute("""
                UPDATE problems
                SET audience_type = CASE
                    WHEN lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%founder%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%предприним%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%основател%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%бизнес%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%business%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%фриланс%'
                    THEN 'entrepreneurs'
                    WHEN lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%пользоват%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%люд%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%родител%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%студент%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%consumer%'
                      OR lower(coalesce(target_audience, '') || ' ' || coalesce(problem_statement, '')) LIKE '%b2c%'
                    THEN 'consumers'
                    ELSE audience_type
                END
                WHERE audience_type IS NULL OR audience_type = '' OR audience_type = 'unknown'
            """)

    # --- Create scrape_logs table if missing ---
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scrape_logs'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE scrape_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                discussions_found INTEGER NOT NULL DEFAULT 0,
                problems_created INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                started_at DATETIME,
                completed_at DATETIME,
                triggered_by VARCHAR(20) NOT NULL DEFAULT 'manual'
            )
        """)
        print("  Migration: created scrape_logs table")

    # --- Create scrape_thread_history table if missing ---
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scrape_thread_history'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE scrape_thread_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                thread_key VARCHAR(300) NOT NULL,
                external_id VARCHAR(200),
                url VARCHAR(500),
                first_seen_at DATETIME NOT NULL,
                last_seen_at DATETIME NOT NULL,
                seen_count INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(source_id) REFERENCES sources(id)
            )
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX uq_thread_history_source_key
            ON scrape_thread_history(source_id, thread_key)
        """)
        print("  Migration: created scrape_thread_history table")

    conn.commit()
    conn.close()


def init_db():
    """Initialize database - create all tables"""
    print(f"Creating database at: {DB_PATH}")
    Base.metadata.create_all(bind=engine)
    migrate_db()
    print("Database tables created successfully!")


def get_db() -> Session:
    """
    Get database session for dependency injection
    Usage in FastAPI endpoints:
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """Drop all tables and recreate them - USE WITH CAUTION!"""
    print("WARNING: Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")
    init_db()


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print(f"\nDatabase initialized at: {DB_PATH}")
    print("\nYou can now:")
    print("  1. Start the backend: uvicorn api.main:app --reload")
    print("  2. Test scrapers: python -m agents.scrapers.reddit_agent")
