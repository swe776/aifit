from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (
    create_login_token,
    get_current_account,
    hash_password,
    verify_password,
)
from ..database import get_database_session
from ..db_models import Account
from ..schemas import RegisterRequest, AccountResponse, LoginTokenResponse


router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"],
)


# A user registers with an email address and a password to create an account
@router.post(
    "/register",
    response_model=LoginTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_account(
    body: RegisterRequest,
    database: Session = Depends(get_database_session),
):
    # Emails are saved in lower case so the same email cannot be used twice
    email = body.email.lower()
    display_name = body.display_name.strip()

    existing_account = database.scalar(
        select(Account).where(Account.email == email)
    )

    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists with this email.",
        )

    # Only the hashed password is stored and not the actual password itself
    account = Account(
        email=email,
        display_name=display_name,
        password_hash=hash_password(body.password),
    )

    database.add(account)
    database.commit()
    database.refresh(account)

    # The user is logged in right after creating an account
    return LoginTokenResponse(
        access_token=create_login_token(account.id),
        account=AccountResponse.model_validate(account),
    )


# Logging in gives the user a token that ties them to their account
@router.post("/login", response_model=LoginTokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    database: Session = Depends(get_database_session),
):
    email = form.username.lower()

    account = database.scalar(
        select(Account).where(Account.email == email)
    )

    # The same message is shown for a wrong email or password so a hacker cannot guess which one was wrong
    if account is None or not verify_password(
        form.password,
        account.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return LoginTokenResponse(
        access_token=create_login_token(account.id),
        account=AccountResponse.model_validate(account),
    )


# The app uses this to remember who is logged in when the page is opened again
@router.get("/me", response_model=AccountResponse)
def get_my_account(
    account: Account = Depends(get_current_account),
):
    return AccountResponse.model_validate(account)


# Save when the user accepted the privacy notice
@router.post("/privacy-notice", response_model=AccountResponse)
def accept_privacy_notice(
    account: Account = Depends(get_current_account),
    database: Session = Depends(get_database_session),
):
    # Accepting a second time keeps the first date
    if account.privacy_notice_accepted_at is None:
        account.privacy_notice_accepted_at = datetime.now(timezone.utc)
        database.commit()
        database.refresh(account)

    return AccountResponse.model_validate(account)
