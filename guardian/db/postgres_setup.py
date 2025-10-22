"""
PostgreSQL Database Setup for Guardian
========================================

This module provides PostgreSQL database setup and migration utilities for Guardian.
It handles database creation, user setup, and running migrations.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import sql
import os
from pathlib import Path
from typing import Optional, Dict
import logging

# Load .env if present so this script respects your local settings
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

logger = logging.getLogger(__name__)


class PostgresSetup:
    """Handles PostgreSQL database setup and migrations."""
    
    def __init__(self, 
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 database: Optional[str] = None,
                 user: Optional[str] = None,
                 password: Optional[str] = None):
        """
        Initialize with explicit args or fall back to environment variables:
          - PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE
          - POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB
        Sensible defaults for Docker Compose:
          host=db, port=5432, user=guardian, password=guardian, database=guardian
        """
        # Prefer standard PG* env, then docker POSTGRES_* vars, then sensible local defaults
        self.host = host or os.getenv("PGHOST") or "db"
        self.port = int(port or os.getenv("PGPORT") or 5432)
        self.database = database or os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB") or "guardian"
        self.user = user or os.getenv("PGUSER") or os.getenv("POSTGRES_USER") or "guardian"
        # Allow either PGPASSWORD or POSTGRES_PASSWORD
        self.password = password or os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD") or "guardian"
        
    def test_connection(self) -> bool:
        """Test connection to PostgreSQL server."""
        try_dbs = ["postgres", self.database]
        for dbname in try_dbs:
            try:
                conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=dbname
                )
                conn.close()
                return True
            except Exception:
                continue
        return False
    
    def create_database(self) -> bool:
        """Create the Guardian database if it doesn't exist."""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cur:
                # Check if database exists
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.database,)
                )
                if not cur.fetchone():
                    # Create database (identifier-safe)
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.database)))
                    logger.info(f"Database '{self.database}' created successfully")
                else:
                    logger.info(f"Database '{self.database}' already exists")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            return False
    
    def create_user(self, new_user: str, new_password: str) -> bool:
        """Create a new PostgreSQL user for Guardian."""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cur:
                # Check if user exists
                cur.execute(
                    "SELECT 1 FROM pg_user WHERE usename = %s",
                    (new_user,)
                )
                if not cur.fetchone():
                    # Create user
                    cur.execute(
                        f"CREATE USER {new_user} WITH PASSWORD %s",
                        (new_password,)
                    )
                    logger.info(f"User '{new_user}' created successfully")
                else:
                    logger.info(f"User '{new_user}' already exists")
                
                # Grant privileges on database
                cur.execute(
                    f"GRANT ALL PRIVILEGES ON DATABASE {self.database} TO {new_user}"
                )
                logger.info(f"Granted privileges on '{self.database}' to '{new_user}'")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    def run_migration(self, migration_file: str) -> bool:
        """Run a SQL migration file."""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            
            with conn.cursor() as cur:
                # Read and execute migration
                migration_path = Path(migration_file)
                if not migration_path.exists():
                    logger.error(f"Migration file not found: {migration_file}")
                    return False
                
                with open(migration_file, 'r') as f:
                    sql_content = f.read()
                
                # Execute the migration
                cur.execute(sql_content)
                conn.commit()
                
                logger.info(f"Migration '{migration_file}' executed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to run migration: {e}")
            return False
    
    def get_connection(self):
        """Get a PostgreSQL connection."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )
    
    def test_tables(self) -> Dict[str, bool]:
        """Test if all required tables exist."""
        required_tables = [
            'generated_images',
            'uploaded_images', 
            'generated_documents',
            'uploaded_documents'
        ]
        
        results = {}
        
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                for table in required_tables:
                    cur.execute(
                        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                        (table,)
                    )
                    exists = cur.fetchone() is not None
                    results[table] = exists
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to test tables: {e}")
            return {table: False for table in required_tables}


def setup_postgres_database(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    admin_user: Optional[str] = None,
    admin_password: Optional[str] = None,
    app_user: Optional[str] = None,
    app_password: Optional[str] = None
) -> bool:
    """
    Complete PostgreSQL setup for Guardian.
    
    Args:
        host: PostgreSQL host (default from $PGHOST or "db")
        port: PostgreSQL port (default from $PGPORT or 5432)
        database: Database name (default from $PGDATABASE or "guardian")
        admin_user: Admin/superuser (default from $PGUSER/$POSTGRES_USER or "guardian")
        admin_password: Admin password (default from $PGPASSWORD/$POSTGRES_PASSWORD or "guardian")
        app_user: Optional application user to create
        app_password: Password for app_user (if provided)
        
    Returns:
        True if setup successful, False otherwise
    """
    # Let PostgresSetup pull from env by default; explicit args override if provided
    setup = PostgresSetup(
        host=host,
        port=port,
        database=database,
        user=admin_user,
        password=admin_password
    )
    
    logger.info("Starting PostgreSQL setup for Guardian...")
    
    # Test connection
    if not setup.test_connection():
        logger.error("Cannot connect to PostgreSQL server")
        return False
    
    # Create database
    if not setup.create_database():
        logger.error("Failed to create database")
        return False
    
    # Create application user
    if app_password:
        if not setup.create_user(app_user, app_password):
            logger.error("Failed to create application user")
            return False
    
    logger.info("PostgreSQL setup completed successfully!")
    return True


# Run using environment (see README / .env):
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
# or Docker-style:
#   POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = setup_postgres_database(
        # allow overrides via env, leave args None to use PostgresSetup defaults
        app_user=None,
        app_password=None  # skip creating a separate app user unless provided
    )
    if success:
        print("✅ PostgreSQL setup completed!")
    else:
        print("❌ PostgreSQL setup failed!")
