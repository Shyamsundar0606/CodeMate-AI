"""Create only an absent local GitHub encryption key; never display credentials."""

from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values


def main() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.exists():
        raise SystemExit("Create backend/.env with setup_local.py first")
    values = dotenv_values(path)
    current = values.get("GITHUB_TOKEN_ENCRYPTION_KEY")
    if current:
        try:
            Fernet(current.encode())
        except ValueError as exc:
            raise SystemExit("Existing key is invalid; no configuration was changed") from exc
        print("GitHub encryption key already configured; preserved.")
        return
    if "GITHUB_TOKEN_ENCRYPTION_KEY" in values:
        raise SystemExit(
            "Existing blank key was preserved. Remove only the empty key line before generating it."
        )
    with path.open("a", encoding="utf-8") as file:
        file.write("\nGITHUB_TOKEN_ENCRYPTION_KEY=" + Fernet.generate_key().decode() + "\n")
    print(
        "Generated an independent local encryption key in ignored backend/.env. "
        "No GitHub App was registered."
    )


if __name__ == "__main__":
    main()
