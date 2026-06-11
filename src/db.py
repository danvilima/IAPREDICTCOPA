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
    return create_engine(database_url)

def get_raw_connection():
    """Returns a raw psycopg2 connection."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set in environment variables.")
    return psycopg2.connect(database_url)
