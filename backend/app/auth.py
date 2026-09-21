from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.orm import Session

from .config import settings
from .database import get_database_session
from .db_models import Account


# Passwords are hashed with Argon2 so a leaked database does not share any passwords
password_hasher = PasswordHash((Argon2Hasher(),))

# Read the login token that the app sends with each request
login_token_reader = OAuth2PasswordBearer(
    tokenUrl="/api/accounts/login",
)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hasher.verify(password, stored_hash)


def create_login_token(account_id: int) -> str:
    # The token ties the user to their account and sets an expiry for the session
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes,
    )

    payload = {
        "sub": str(account_id),
        "exp": expires_at,
    }

    # Sign the token so it cannot be changed
    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


# Every route that needs a login uses this to see which account is making the request
def get_current_account(
    token: str = Depends(login_token_reader),
    database: Session = Depends(get_database_session),
) -> Account:
    # The same error is given for every login problem
    login_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Your login was unsuccessful. Please try again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        account_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise login_error

    # Refuse the token when the account no longer exists
    account = database.get(Account, account_id)

    if account is None:
        raise login_error

    return account
