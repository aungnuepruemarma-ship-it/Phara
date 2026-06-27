import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_experiment(client: AsyncClient, researcher_token: str):
    proj = await client.post(
        "/api/v1/projects",
        json={"name": "Exp Project"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    pid = proj.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/experiments",
        json={"title": "Exp 1", "description": "Test", "parameters": {"lr": 0.01}},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Exp 1"
    assert data["status"] == "draft"
    assert data["parameters"]["lr"] == 0.01


@pytest.mark.asyncio
async def test_update_experiment_status(client: AsyncClient, researcher_token: str):
    proj = await client.post(
        "/api/v1/projects",
        json={"name": "Status Project"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    pid = proj.json()["id"]

    exp = await client.post(
        f"/api/v1/projects/{pid}/experiments",
        json={"title": "Status Exp"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    eid = exp.json()["id"]

    resp = await client.put(
        f"/api/v1/projects/{pid}/experiments/{eid}",
        json={"status": "running"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_get_experiment_detail(client: AsyncClient, researcher_token: str):
    proj = await client.post(
        "/api/v1/projects",
        json={"name": "Detail Project"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    pid = proj.json()["id"]

    exp = await client.post(
        f"/api/v1/projects/{pid}/experiments",
        json={"title": "Detail Exp"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    eid = exp.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{pid}/experiments/{eid}",
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert resp.status_code == 200
    assert "hypotheses" in resp.json()
    assert resp.json()["hypotheses"] == []
