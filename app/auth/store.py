"""Thin shim — delegates to user_repository. Kept for backward compatibility."""

from app.auth.repositories.user_repository import (
    create_no_commit as create_user,
    find_by_email as get_by_email,
    find_by_id as get_by_id,
    find_by_username as get_by_username,
    username_exists,
)

__all__ = [
    "create_user",
    "get_by_email",
    "get_by_id",
    "get_by_username",
    "username_exists",
]
