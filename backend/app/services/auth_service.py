import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import unauthorized
from app.core.security import (
    hash_password,
    new_refresh_token,
    password_hasher,
    token_hash,
    verify_password,
)
from app.models import LoginThrottle, RefreshSession, Role, User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest


class AuthService:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)

    def register(self, data: RegisterRequest) -> User:
        user = User(
            email=str(data.email),
            username=data.username,
            password_hash=hash_password(data.password.get_secret_value()),
            role=Role.USER,
        )
        self.session.add(user)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(409, "Email or username already registered") from exc
        return user

    def throttle(self, email: str, address: str) -> None:
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=self.settings.login_window_seconds)
        exceeded = False
        # Consistent lock order prevents deadlocks across simultaneous clients.
        entries = [
            ("account:" + email, self.settings.login_account_limit),
            ("ip:" + address, self.settings.login_ip_limit),
        ]
        for subject, limit in entries:
            key = hashlib.sha256(subject.encode()).hexdigest()
            expired = LoginThrottle.window_start <= cutoff
            statement = insert(LoginThrottle).values(key=key, window_start=now, attempts=1)
            statement = statement.on_conflict_do_update(
                index_elements=[LoginThrottle.key],
                set_={
                    "attempts": case((expired, 1), else_=LoginThrottle.attempts + 1),
                    "window_start": case((expired, now), else_=LoginThrottle.window_start),
                },
            ).returning(LoginThrottle.attempts)
            attempts = self.session.scalar(statement)
            exceeded = exceeded or (attempts is not None and attempts > limit)
        # Persist limits even for failed authentication or a rate-limited response.
        self.session.commit()
        if exceeded:
            raise HTTPException(
                429,
                "Too many login attempts",
                headers={"Retry-After": str(self.settings.login_window_seconds)},
            )

    def _new_session(self, user_id: uuid.UUID) -> str:
        token = new_refresh_token()
        self.session.add(
            RefreshSession(
                user_id=user_id,
                token_hash=token_hash(token),
                expires_at=datetime.now(UTC)
                + timedelta(days=self.settings.refresh_token_expire_days),
            )
        )
        return token

    def login(self, email: str, password: str, address: str) -> tuple[User, str]:
        self.throttle(email, address)
        user = self.users.by_email(email)
        valid = verify_password(user.password_hash if user else None, password)
        if not valid or user is None or not user.is_active:
            raise unauthorized()
        if password_hasher.check_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        token = self._new_session(user.id)
        self.session.commit()
        return user, token

    def active_session(self, token: str, *, lock: bool = False) -> tuple[RefreshSession, User]:
        statement = select(RefreshSession).where(RefreshSession.token_hash == token_hash(token))
        if lock:
            statement = statement.with_for_update()
        session = self.session.scalar(statement)
        now = datetime.now(UTC)
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise unauthorized()
        user = self.users.by_id(session.user_id)
        if user is None or not user.is_active:
            raise unauthorized()
        return session, user

    def rotate(self, token: str) -> tuple[User, str]:
        session, user = self.active_session(token, lock=True)
        session.revoked_at = datetime.now(UTC)
        replacement = self._new_session(user.id)
        self.session.commit()
        return user, replacement

    def logout(self, token: str) -> None:
        session = self.session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_hash(token))
            .with_for_update()
        )
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
        self.session.commit()
