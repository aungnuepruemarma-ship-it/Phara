import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, researcher_token: str):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "description": "A test", "tags": ["ml", "math"]},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert "ml" in data["tags"]


@pytest.mark.asyncio
async def test_list_projects_scoped_to_owner(client: AsyncClient, researcher_token: str, admin_token: str):
    await client.post(
        "/api/v1/projects",
        json={"name": "Researcher Project"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    resp = await client.get("/api/v1/projects", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Researcher Project" not in names


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, researcher_token: str):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "Old Name"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    pid = create.json()["id"]
    resp = await client.put(
        f"/api/v1/projects/{pid}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, researcher_token: str):
    create = await client.post(
        "/api/v1/projects",
        json={"name": "To Delete"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    pid = create.json()["id"]
    resp = await client.delete(f"/api/v1/projects/{pid}", headers={"Authorization": f"Bearer {researcher_token}"})
    assert resp.status_code == 204
    resp2 = await client.get(f"/api/v1/projects/{pid}", headers={"Authorization": f"Bearer {researcher_token}"})
    assert resp2.status_code == 404
