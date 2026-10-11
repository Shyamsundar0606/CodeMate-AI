from fastapi import HTTPException


class GitHubError(HTTPException):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 424,
        *,
        retry_after: int | None = None,
        reset_at: int | None = None,
    ):
        detail = {"code": code, "message": message}
        if retry_after is not None:
            detail["retry_after"] = retry_after
        if reset_at is not None:
            detail["reset_at"] = reset_at
        super().__init__(
            status_code=status,
            detail=detail,
            headers={
                "Cache-Control": "no-store",
                **({"Retry-After": str(retry_after)} if retry_after else {}),
            },
        )


def malformed() -> GitHubError:
    return GitHubError(
        "GITHUB_INVALID_RESPONSE",
        "GitHub returned incomplete or invalid data. Try refreshing.",
        502,
    )
