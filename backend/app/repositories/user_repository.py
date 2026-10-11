import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def page(self, offset: int, limit: int) -> tuple[list[User], int]:
        users = list(
            self.session.scalars(
                select(User).order_by(User.created_at, User.id).offset(offset).limit(limit)
            )
        )
        total = self.session.scalar(select(func.count()).select_from(User)) or 0
        return users, total
