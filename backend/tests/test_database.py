from datetime import UTC, datetime, timedelta

import pytest
from alembic.config import Config
from conftest import BACKEND
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.security import hash_password, token_hash
from app.models import RefreshSession, User


def make_user(email="one@example.com", username="one"):
    return User(email=email, username=username, password_hash=hash_password("StrongPassword123!"))


def test_postgres_persistence_and_rollback(db, session_factory):
    user = make_user()
    db.add(user)
    db.commit()
    with session_factory() as other:
        assert other.get(User, user.id).email == "one@example.com"
    db.add(make_user("two@example.com", "two"))
    db.flush()
    db.rollback()
    assert len(list(db.scalars(select(User)))) == 1


@pytest.mark.parametrize("field", ["email", "username"])
def test_database_unique_constraints(db, field):
    db.add(make_user())
    db.commit()
    db.add(
        make_user(
            "one@example.com" if field == "email" else "two@example.com",
            "one" if field == "username" else "two",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert len(list(db.scalars(select(User)))) == 1


def test_session_foreign_key_and_unique_hash(db):
    user = make_user()
    db.add(user)
    db.flush()
    session = RefreshSession(
        user_id=user.id,
        token_hash=token_hash("secret"),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(session)
    db.commit()
    assert db.get(RefreshSession, session.id).expires_at.tzinfo is not None
    db.add(
        RefreshSession(
            user_id=user.id, token_hash=session.token_hash, expires_at=session.expires_at
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.delete(user)
    db.commit()
    assert not list(db.scalars(select(RefreshSession)))


def test_migration_matches_metadata(engine):
    config = Config(str(BACKEND / "alembic.ini"))
    command.check(config)
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004_voice_agent"
        )
        assert connection.scalar(text("SELECT current_database()")) == "codemate_test_db"


def test_initial_migration_roundtrip(engine):
    # Only dedicated test database, guarded in conftest; never downgrade development.
    config = Config(str(BACKEND / "alembic.ini"))
    try:
        command.downgrade(config, "base")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT to_regclass('users')")) is None
    finally:
        command.upgrade(config, "head")
    command.check(config)


def test_test_role_cannot_connect_development(settings):
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import OperationalError

    url = make_url(settings.database_url.get_secret_value()).set(database="codemate_db")
    engine = create_engine(url, hide_parameters=True)
    try:
        with pytest.raises(OperationalError):
            with engine.connect():
                pass
    finally:
        engine.dispose()
