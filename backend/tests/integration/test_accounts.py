# Integration tests for accounts, logging in and the privacy notice
def test_register_account(client):
    response = client.post(
        "/api/accounts/register",
        json={
            "email": "swetha@gmail.com",
            "display_name": "Swetha",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["account"]["email"] == "swetha@gmail.com"
    assert body["account"]["display_name"] == "Swetha"
    assert "password" not in body["account"]
    assert "password_hash" not in body["account"]


def test_duplicate_email_is_rejected(client):
    account = {
        "email": "timo@gmail.com",
        "display_name": "Timo",
        "password": "password123",
    }

    first_response = client.post(
        "/api/accounts/register",
        json=account,
    )

    second_response = client.post(
        "/api/accounts/register",
        json=account,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_email_is_not_case_sensitive(client):
    first_response = client.post(
        "/api/accounts/register",
        json={
            "email": "GEORGE@gmail.com",
            "display_name": "George",
            "password": "password123",
        },
    )

    second_response = client.post(
        "/api/accounts/register",
        json={
            "email": "george@gmail.com",
            "display_name": "George",
            "password": "password123",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_invalid_email_is_rejected(client):
    response = client.post(
        "/api/accounts/register",
        json={
            "email": "invalidemail",
            "display_name": "Tom",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_short_password_is_rejected(client):
    response = client.post(
        "/api/accounts/register",
        json={
            "email": "jack@gmail.com",
            "display_name": "Jack",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_whitespace_display_name_is_rejected(
    client,
):
    response = client.post(
        "/api/accounts/register",
        json={
            "email": "jane@gmail.com",
            "display_name": "   ",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_display_name_is_trimmed(client):
    response = client.post(
        "/api/accounts/register",
        json={
            "email": "swetha@gmail.com",
            "display_name": "  Swetha  ",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    assert (
        response.json()["account"]["display_name"]
        == "Swetha"
    )


def test_login(client):
    client.post(
        "/api/accounts/register",
        json={
            "email": "jane@gmail.com",
            "display_name": "Jane",
            "password": "password123",
        },
    )

    response = client.post(
        "/api/accounts/login",
        data={
            "username": "jane@gmail.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_incorrect_password_is_rejected(client):
    client.post(
        "/api/accounts/register",
        json={
            "email": "amy@gmail.com",
            "display_name": "Amy",
            "password": "password123",
        },
    )

    response = client.post(
        "/api/accounts/login",
        data={
            "username": "amy@gmail.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_account_route_requires_login(client):
    response = client.get(
        "/api/accounts/me"
    )

    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/api/accounts/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401


def test_privacy_notice_is_saved(
    client,
    account_headers,
):
    response = client.get(
        "/api/accounts/me",
        headers=account_headers,
    )

    assert response.status_code == 200

    assert (
        response.json()[
            "privacy_notice_accepted_at"
        ]
        is not None
    )


def test_privacy_notice_is_only_saved_once(
    client,
    account_headers,
):
    first_response = client.post(
        "/api/accounts/privacy-notice",
        headers=account_headers,
    )

    second_response = client.post(
        "/api/accounts/privacy-notice",
        headers=account_headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_date = first_response.json()[
        "privacy_notice_accepted_at"
    ]

    second_date = second_response.json()[
        "privacy_notice_accepted_at"
    ]

    assert first_date == second_date
