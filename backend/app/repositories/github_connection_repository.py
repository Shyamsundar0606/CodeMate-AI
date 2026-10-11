import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GitHubConnection


class GitHubConnectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def owned(self, user_id: uuid.UUID, *, lock: bool = False) -> GitHubConnection | None:
        statement = select(GitHubConnection).where(GitHubConnection.user_id == user_id)
        return self.db.scalar(
            statement.with_for_update().execution_options(populate_existing=True)
            if lock
            else statement
        )
