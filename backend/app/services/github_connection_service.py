import base64
import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import token_hash
from app.integrations.github.client import GitHubClient
from app.integrations.github.crypto import CredentialCipher
from app.integrations.github.exceptions import GitHubError, malformed
from app.integrations.github.schemas import ConnectionResponse, normalize
from app.models import GitHubConnection, GitHubOAuthState, RefreshSession, User
from app.repositories.github_connection_repository import GitHubConnectionRepository

BROWSER_COOKIE = "codemate_github_state"
CALLBACK_PATH = "/api/v1/github/callback"


class GitHubConnectionService:
    def __init__(self, db: Session, settings: Settings, client: GitHubClient):
        self.db = db
        self.settings = settings
        self.client = client
        self.repo = GitHubConnectionRepository(db)

    def configured(self) -> None:
        if not self.settings.github_configured:
            raise GitHubError(
                "GITHUB_NOT_CONFIGURED",
                "GitHub integration is not configured. Follow the local GitHub App setup guide.",
                503,
            )

    def status(self, user_id: uuid.UUID) -> ConnectionResponse:
        item = self.repo.owned(user_id)
        common = {
            "configured": self.settings.github_configured,
            "install_url": f"https://github.com/apps/{self.settings.github_app_slug}/installations/new"
            if self.settings.github_app_slug
            else None,
        }
        if item is None:
            return ConnectionResponse(status="disconnected", **common)
        return ConnectionResponse(
            status=item.connection_status,
            id=str(item.id),
            github_user_id=item.github_user_id,
            github_login=item.github_login,
            github_display_name=item.github_display_name,
            github_avatar_url=item.github_avatar_url,
            granted_permissions=item.granted_permissions,
            connected_at=item.connected_at,
            last_verified_at=item.last_verified_at,
            **common,
        )

    def start(self, user: User, session: RefreshSession) -> tuple[str, str]:
        self.configured()
        self.db.scalar(select(User).where(User.id == user.id).with_for_update())
        self.db.execute(delete(GitHubOAuthState).where(GitHubOAuthState.user_id == user.id))
        state = secrets.token_urlsafe(32)
        browser = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        self.db.add(
            GitHubOAuthState(
                state_hash=token_hash(state),
                user_id=user.id,
                session_id=session.id,
                browser_hash=token_hash(browser),
                encrypted_verifier=CredentialCipher(self.settings).encrypt(
                    user.id, "pkce:" + token_hash(state), verifier
                ),
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
        self.db.commit()
        params = {
            "client_id": self.settings.github_client_id,
            "redirect_uri": self.settings.github_redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "offline_access",
            "allow_signup": "false",
        }
        return "https://github.com/login/oauth/authorize?" + urlencode(params), browser

    def finish(self, state: str, browser: str, code: str | None, cancelled: bool) -> None:
        self.configured()
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", state) or not re.fullmatch(
            r"[A-Za-z0-9_-]{43}", browser
        ):
            raise GitHubError(
                "GITHUB_INVALID_STATE", "GitHub authorization state is invalid. Start again.", 400
            )
        candidate = self.db.get(GitHubOAuthState, token_hash(state))
        if candidate is None:
            raise GitHubError(
                "GITHUB_INVALID_STATE", "GitHub authorization state is invalid. Start again.", 400
            )
        user = self.db.scalar(select(User).where(User.id == candidate.user_id).with_for_update())
        entry = self.db.scalar(
            select(GitHubOAuthState)
            .where(GitHubOAuthState.state_hash == token_hash(state))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        now = datetime.now(UTC)
        if (
            entry is None
            or entry.consumed_at
            or entry.expires_at <= now
            or not secrets.compare_digest(entry.browser_hash, token_hash(browser))
        ):
            raise GitHubError(
                "GITHUB_INVALID_STATE",
                "GitHub authorization expired or belongs to a different browser. Start again.",
                400,
            )
        session = self.db.get(RefreshSession, entry.session_id)
        if (
            not user
            or not user.is_active
            or not session
            or session.revoked_at
            or session.expires_at <= now
            or session.user_id != user.id
        ):
            raise GitHubError(
                "GITHUB_SESSION_CHANGED",
                "The initiating CodeMate session is no longer active. Sign in and reconnect.",
                400,
            )
        entry.consumed_at = now
        try:
            if cancelled:
                raise GitHubError(
                    "GITHUB_AUTHORIZATION_CANCELLED", "GitHub authorization was cancelled.", 400
                )
            if not code or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", code):
                raise GitHubError(
                    "GITHUB_MISSING_CODE",
                    "GitHub did not provide a valid authorization code. Start again.",
                    400,
                )
            cipher = CredentialCipher(self.settings)
            verifier = cipher.decrypt(user.id, "pkce:" + entry.state_hash, entry.encrypted_verifier)
            tokens = self.client.exchange(
                {
                    "code": code,
                    "code_verifier": verifier,
                    "redirect_uri": self.settings.github_redirect_uri,
                }
            )
            data, _ = self.client.json("/user", tokens["access_token"])
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("id"), int)
                or data["id"] <= 0
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", data.get("login", ""))
            ):
                raise malformed()
            installs, _ = self.client.json(
                "/user/installations", tokens["access_token"], {"per_page": 100, "page": 1}
            )
            if not isinstance(installs, dict) or not isinstance(
                installs.get("installations"), list
            ):
                raise malformed()
            permissions = {}
            for value in installs["installations"]:
                installation = normalize("installations", value)
                permissions.update(installation.permissions)
            # Logout/rotation can happen while GitHub is responding. Recheck the
            # originating session under a row lock before saving any credentials.
            active = self.db.scalar(
                select(RefreshSession)
                .where(RefreshSession.id == entry.session_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if not active or active.revoked_at or active.expires_at <= datetime.now(UTC):
                raise GitHubError(
                    "GITHUB_SESSION_CHANGED",
                    "The initiating session changed. Sign in and reconnect.",
                    400,
                )
            item = self.repo.owned(user.id, lock=True)
            if item is None:
                item = GitHubConnection(user_id=user.id)
                self.db.add(item)
            item.github_user_id = data["id"]
            item.github_login = data["login"]
            item.github_display_name = (
                data.get("name")[:200] if isinstance(data.get("name"), str) else None
            )
            item.github_avatar_url = f"https://avatars.githubusercontent.com/u/{data['id']}?v=4"
            item.granted_permissions = permissions
            self.save_tokens(item, tokens)
            item.connection_status = "connected"
            item.last_verified_at = now
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            used = self.db.get(GitHubOAuthState, token_hash(state))
            if used:
                used.consumed_at = datetime.now(UTC)
                self.db.commit()
            raise GitHubError(
                "GITHUB_ACCOUNT_ALREADY_LINKED",
                (
                    "This GitHub account is already linked to "
                    "another CodeMate account. Disconnect it there first."
                ),
                409,
            ) from exc
        except GitHubError:
            self.db.commit()  # Consume validated state even on cancellation or upstream failure.
            raise

    def save_tokens(self, item: GitHubConnection, tokens: dict) -> None:
        cipher = CredentialCipher(self.settings)
        now = datetime.now(UTC)
        item.encrypted_access_token = cipher.encrypt(item.user_id, "access", tokens["access_token"])
        item.encrypted_refresh_token = (
            cipher.encrypt(item.user_id, "refresh", tokens["refresh_token"])
            if tokens.get("refresh_token")
            else None
        )
        item.token_expires_at = (
            now + timedelta(seconds=tokens["expires_in"]) if tokens.get("expires_in") else None
        )
        item.refresh_expires_at = (
            now + timedelta(seconds=tokens["refresh_token_expires_in"])
            if tokens.get("refresh_token_expires_in")
            else None
        )

    def invalidate(self, item: GitHubConnection) -> None:
        item.connection_status = "reauthorization_required"
        item.encrypted_access_token = None
        item.encrypted_refresh_token = None
        self.db.commit()

    def credentials(self, user_id: uuid.UUID) -> tuple[GitHubConnection, str]:
        self.configured()
        item = self.repo.owned(user_id, lock=True)
        if item is None:
            raise GitHubError(
                "GITHUB_NOT_CONNECTED", "Connect your GitHub account to view this page.", 409
            )
        if item.connection_status != "connected" or not item.encrypted_access_token:
            raise GitHubError(
                "GITHUB_REAUTHORIZATION_REQUIRED",
                "GitHub authorization needs to be renewed. Reconnect your account.",
            )
        cipher = CredentialCipher(self.settings)
        now = datetime.now(UTC)
        if item.token_expires_at and item.token_expires_at <= now + timedelta(seconds=60):
            if not item.encrypted_refresh_token or (
                item.refresh_expires_at and item.refresh_expires_at <= now
            ):
                self.invalidate(item)
                raise GitHubError(
                    "GITHUB_REAUTHORIZATION_REQUIRED",
                    "GitHub credentials expired. Reconnect your account.",
                )
            refresh = cipher.decrypt(user_id, "refresh", item.encrypted_refresh_token)
            try:
                tokens = self.client.exchange(
                    {"grant_type": "refresh_token", "refresh_token": refresh}
                )
            except GitHubError as exc:
                if exc.detail["code"] in {
                    "GITHUB_AUTHORIZATION_FAILED",
                    "GITHUB_REAUTHORIZATION_REQUIRED",
                }:
                    self.invalidate(item)
                raise
            if not tokens.get("refresh_token"):
                self.invalidate(item)
                raise malformed()
            self.save_tokens(item, tokens)
            # Persist rotated credentials even if the following read fails.
            self.db.commit()
            item = self.repo.owned(user_id, lock=True)
            if item is None or item.connection_status != "connected":
                raise GitHubError("GITHUB_NOT_CONNECTED", "Connect GitHub again.", 409)
        return item, cipher.decrypt(user_id, "access", item.encrypted_access_token)

    def disconnect(self, user_id: uuid.UUID) -> dict:
        self.db.scalar(select(User).where(User.id == user_id).with_for_update())
        self.db.execute(delete(GitHubOAuthState).where(GitHubOAuthState.user_id == user_id))
        item = self.repo.owned(user_id, lock=True)
        revoked = False
        if item:
            try:
                if self.settings.github_configured and item.encrypted_access_token:
                    token = CredentialCipher(self.settings).decrypt(
                        user_id, "access", item.encrypted_access_token
                    )
                    revoked = self.client.revoke(token)
            except GitHubError:
                pass  # Local deletion succeeds even when remote revocation cannot be confirmed.
            self.db.delete(item)
        self.db.commit()
        return {
            "disconnected": True,
            "remote_revoked": revoked,
            "message": "Disconnected. GitHub authorization was revoked."
            if revoked
            else (
                "Disconnected locally. Remote revocation was not "
                "confirmed; review Authorized GitHub Apps in GitHub settings."
            ),
        }
