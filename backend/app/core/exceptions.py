from fastapi import HTTPException


def unauthorized() -> HTTPException:
    return HTTPException(
        401, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"}
    )
