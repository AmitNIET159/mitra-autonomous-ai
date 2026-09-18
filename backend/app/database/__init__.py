"""Database package for local SQLite persistence."""
from app.database.connection import get_db_path, init_db

__all__ = ["get_db_path", "init_db"]
