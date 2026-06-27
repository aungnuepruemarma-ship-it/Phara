import io
import json
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_paper(client: AsyncClient, researcher_token: str, mocker):
    mocker.patch("app.services.paper_service._embed_paper")

    proj = await client.post(
        "/api/v1/projects",
        json={"name": "Paper Project"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    pid = proj.json()["id"]

    metadata = json.dumps({"title": "Test Paper", "authors": ["Alice"], "year": 2024})
    pdf_bytes = b"%PDF-1.4 fake pdf content"

    resp = await client.post(
        f"/api/v1/projects/{pid}/papers",
        headers={"Authorization": f"Bearer {researcher_token}"},
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"metadata": metadata},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Paper"
    assert data["embedding_status"] == "pending"


@pytest.mark.asyncio
async def test_list_papers(client: AsyncClient, researcher_token: str, mocker):
    mocker.patch("app.services.paper_service._embed_paper")

    proj = await client.post(
        "/api/v1/projects",
        json={"name": "List Papers Project"},
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    pid = proj.json()["id"]

    for i in range(2):
        await client.post(
            f"/api/v1/projects/{pid}/papers",
            headers={"Authorization": f"Bearer {researcher_token}"},
            files={"file": (f"p{i}.pdf", io.BytesIO(b"%PDF fake"), "application/pdf")},
            data={"metadata": json.dumps({"title": f"Paper {i}"})},
        )

    resp = await client.get(f"/api/v1/projects/{pid}/papers", headers={"Authorization": f"Bearer {researcher_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2
