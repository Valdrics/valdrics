from uuid import UUID
from datetime import timedelta

from app.shared.core.auth import create_access_token


def create_test_token(user_id: UUID, email: str):
    """Generate a valid test JWT for Supabase authentication."""
    return create_access_token(
        {"sub": str(user_id), "email": email},
        expires_delta=timedelta(hours=1),
    )
