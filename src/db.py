import os
from sqlalchemy import create_engine
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    """Returns a SQLAlchemy engine."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set in environment variables.")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return create_engine(database_url)


def get_raw_connection():
    """Returns a raw psycopg2 connection."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set in environment variables.")

    if database_url.startswith("postgresql+psycopg2://"):
        database_url = database_url.replace(
            "postgresql+psycopg2://", "postgresql://", 1
        )

    return psycopg2.connect(database_url)
