import hmac
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def verify_token_str(token: str, valid_keys: dict[str, str]) -> str | None:
    """Verify raw token against authorized keys dictionary using constant-time comparison."""
    if not token or not valid_keys:
        return None

    for valid_token, owner in valid_keys.items():
        if hmac.compare_digest(valid_token, token):
            return owner

    return None


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    """
    Authenticate request via Bearer token.
    Enforces strict access control without bypassing 401.
    """
    if credentials and credentials.scheme.lower() == "bearer":
        valid_keys = getattr(request.app.state, "keys", {})
        owner = verify_token_str(credentials.credentials, valid_keys)
        if owner:
            return owner

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid bearer token required",
        headers={"WWW-Authenticate": "Bearer"},
    )
