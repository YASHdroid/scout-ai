
import os
import secrets

from fastapi import Header, HTTPException


def verify_internal_service(
    x_internal_secret: str | None = Header(default=None),
):
    expected_secret = os.getenv("INTERNAL_API_SECRET")

    if not expected_secret:
        raise HTTPException(
            status_code=500,
            detail="Internal API secret is not configured.",
        )

    if (
        not x_internal_secret
        or not secrets.compare_digest(
            x_internal_secret,
            expected_secret,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden.",
        )

