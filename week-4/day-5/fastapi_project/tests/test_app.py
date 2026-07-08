import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready(client):
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["dependencies"]["database"] is True


@pytest.mark.asyncio
async def test_document_crud_roundtrip(client):
    create_resp = await client.post(
        "/documents/", json={"title": "Hello", "content": "World"}
    )
    assert create_resp.status_code == 201
    doc_id = create_resp.json()["id"]

    get_resp = await client.get(f"/documents/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Hello"

    delete_resp = await client.delete(f"/documents/{doc_id}")
    assert delete_resp.status_code == 204
