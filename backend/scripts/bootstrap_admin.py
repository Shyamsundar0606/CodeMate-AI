"""Explicit operator action; no default administrator or public promotion endpoint."""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import build_engine, build_session_factory
from app.models import Role, User
from app.schemas.auth import RegisterRequest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an administrator; never promotes an existing user"
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Administrator password: ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords differ")
    data = RegisterRequest(email=args.email, username=args.username, password=password)
    engine = build_engine(Settings())
    try:
        with build_session_factory(engine)() as session:
            session.add(
                User(
                    email=str(data.email),
                    username=data.username,
                    password_hash=hash_password(password),
                    role=Role.ADMIN,
                )
            )
            session.commit()
    except Exception:
        raise SystemExit(
            "Administrator creation failed. Check uniqueness and database readiness."
        ) from None
    finally:
        engine.dispose()
    print("Administrator created.")


if __name__ == "__main__":
    main()
