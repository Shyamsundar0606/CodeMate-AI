from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserPage, UserResponse


def list_users(session: Session, offset: int, limit: int) -> UserPage:
    users, total = UserRepository(session).page(offset, limit)
    return UserPage(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        offset=offset,
        limit=limit,
    )
