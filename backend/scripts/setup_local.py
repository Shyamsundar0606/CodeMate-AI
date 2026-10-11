"""Create missing local settings without printing or replacing existing secrets."""

import secrets
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def append_missing(path: Path, values: dict[str, str]) -> dict[str, str | None]:
    existing = dotenv_values(path) if path.exists() else {}
    missing = {key: value for key, value in values.items() if key not in existing}
    if missing:
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(
                "\n" + "\n".join(f"{key}={value}" for key, value in missing.items()) + "\n"
            )
    return dict(dotenv_values(path))


def main() -> None:
    root = append_missing(
        ROOT / ".env",
        {
            "COMPOSE_PROJECT_NAME": "codemate-ai",
            "CODEMATE_DB_PASSWORD": secrets.token_urlsafe(32),
            "CODEMATE_OWNER_PASSWORD": secrets.token_urlsafe(48),
            "CODEMATE_TEST_PASSWORD": secrets.token_urlsafe(32),
        },
    )
    # Generated URL-safe passwords contain no URL delimiters.
    development_url = (
        f"postgresql+psycopg://codemate_user:{root['CODEMATE_DB_PASSWORD']}"
        "@127.0.0.1:5433/codemate_db"
    )
    test_url = (
        f"postgresql+psycopg://codemate_test_user:{root['CODEMATE_TEST_PASSWORD']}"
        "@127.0.0.1:5433/codemate_test_db"
    )
    append_missing(
        ROOT / "backend" / ".env",
        {
            "APP_ENV": "development",
            "DATABASE_URL": development_url,
            "JWT_SECRET_KEY": secrets.token_urlsafe(48),
            "JWT_ALGORITHM": "HS256",
            "JWT_ISSUER": "codemate-ai",
            "JWT_AUDIENCE": "codemate-api",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            "REFRESH_TOKEN_EXPIRE_DAYS": "7",
            "COOKIE_SECURE": "false",
        },
    )
    append_missing(ROOT / "backend" / ".env.test", {"TEST_DATABASE_URL": test_url})
    print("Missing local settings added. Existing values preserved; secrets not displayed.")


if __name__ == "__main__":
    main()
