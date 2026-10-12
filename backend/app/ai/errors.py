from fastapi import HTTPException


class AIError(HTTPException):
    def __init__(self, code: str, message: str, status: int = 503):
        super().__init__(
            status, {"code": code, "message": message}, headers={"Cache-Control": "no-store"}
        )


def invalid_output() -> AIError:
    return AIError(
        "AI_INVALID_OUTPUT",
        (
            "The local model returned an invalid or unsupported report. "
            "Retry within the attempt limit."
        ),
        502,
    )
