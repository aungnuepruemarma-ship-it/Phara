import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "newuser@test.com",
        "full_name": "New User",
        "password": "securepass",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "researcher"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@test.com", "full_name": "Dup", "password": "securepass"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@test.com", "full_name": "Login", "password": "securepass",
    })
    resp = await client.post("/api/v1/auth/login", json={"email": "login@test.com", "password": "securepass"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wp@test.com", "full_name": "WP", "password": "securepass",
    })
    resp = await client.post("/api/v1/auth/login", json={"email": "wp@test.com", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_returns_user(client: AsyncClient, researcher_token: str):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {researcher_token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "researcher"
