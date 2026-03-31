"""
User feature module.

Importing this package loads ORM models for Alembic autogenerate.
"""

from app.user.models import UserModel  # noqa: F401
from app.user.enums import AccountType  # noqa: F401
