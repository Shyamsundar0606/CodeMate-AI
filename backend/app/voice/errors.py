from fastapi import HTTPException


def error(code: str, message: str, status: int = 422):
    return HTTPException(status, {"code": "VOICE_" + code, "message": message})
