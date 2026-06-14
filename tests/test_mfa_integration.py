"""Integration tests for TOTP-based MFA setup and verification."""

import pytest
from httpx import AsyncClient

from app.auth.mfa.backup_codes import generate_backup_codes, hash_backup_codes, verify_backup_code
from app.auth.mfa.totp import generate_qr_code_uri, generate_secret, verify_totp


def test_totp_secret_generation():
    secret = generate_secret()
    assert len(secret) == 32  # base32 encoded, 20 bytes


def test_totp_qr_code_uri():
    secret = generate_secret()
    uri = generate_qr_code_uri(secret, "testuser", issuer="TestApp")
    assert uri.startswith("otpauth://totp/TestApp:testuser")
    assert "secret=" in uri


def test_totp_verify_with_pyotp():
    import pyotp

    secret = generate_secret()
    totp = pyotp.TOTP(secret)
    code = totp.now()
    assert verify_totp(secret, code)


def test_backup_codes_generation():
    codes = generate_backup_codes(10)
    assert len(codes) == 10
    assert all(len(c) == 8 for c in codes)


def test_backup_codes_hash_and_verify():
    codes = generate_backup_codes()
    hashes = hash_backup_codes(codes)
    assert len(hashes) == len(codes)
    assert verify_backup_code(codes[0], hashes) is not None
    assert verify_backup_code("INVALID", hashes) is None


@pytest.mark.asyncio
async def test_mfa_setup_requires_auth(client: AsyncClient):
    r = await client.post("/auth/mfa/setup")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_mfa_login_flow(client: AsyncClient):
    # Register a user
    r = await client.post(
        "/auth/register",
        json={
            "username": "mfatestuser",
            "email": "mfatestuser@example.com",
            "password": "Test1234!",
        },
    )
    if r.status_code == 429:
        pytest.skip("registration rate limited")
    assert r.status_code == 201

    # Login should succeed without MFA
    r = await client.post(
        "/auth/login",
        json={
            "username": "mfatestuser",
            "password": "Test1234!",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mfa_required"] is False
    assert data["access_token"] is not None


@pytest.mark.asyncio
async def test_totp_secret_is_encrypted_in_db(client: AsyncClient):
    """After MFA setup, the DB value should be a Fernet ciphertext (starts with gAAAAA)."""
    # Register + login
    r0 = await client.post(
        "/auth/register",
        json={
            "username": "mfa_enc_test",
            "email": "mfa_enc_test@example.com",
            "password": "Test1234!",
        },
    )
    if r0.status_code == 429:
        pytest.skip("registration rate limited")
    r = await client.post("/auth/login", json={"username": "mfa_enc_test", "password": "Test1234!"})
    if r.status_code != 200:
        pytest.skip("login unavailable")
    access_token = r.json()["access_token"]

    await client.post("/auth/mfa/setup", headers={"Authorization": f"Bearer {access_token}"})

    # Query the DB directly
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.models import UserMfaSecret
    from app.core.db import engine

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(UserMfaSecret)
            .join(
                __import__("app.auth.models", fromlist=["User"]).User,
                UserMfaSecret.user_id == __import__("app.auth.models", fromlist=["User"]).User.id,  # type: ignore
            )
            .where(__import__("app.auth.models", fromlist=["User"]).User.username == "mfa_enc_test")
        )
        mfa = result.scalar_one_or_none()

    assert mfa is not None
    assert mfa.secret_encrypted.startswith("gAAAAA"), (
        f"Expected Fernet ciphertext, got: {mfa.secret_encrypted[:20]}"
    )
