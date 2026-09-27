"""
SQLAlchemy declarative base shared by all ORM models.

Import ``Base`` here instead of creating a new one per model - this ensures
Alembic's ``autogenerate`` sees every table in a single ``MetaData`` object.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Project-wide declarative base."""
