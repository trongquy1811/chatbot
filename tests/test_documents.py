import io
from tests.mocks import TEST_TOKEN


def test_upload_text_document(app_and_client):
    client, _ = app_and_client
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

    sample_content = b"This is a test document explaining the Agent Harness architecture and core principles."
    files = {"file": ("test_doc.txt", io.BytesIO(sample_content), "text/plain")}

    response = client.post("/documents", headers=headers, files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_doc.txt"
    assert data["status"] == "ready"
    assert data["chunks"] >= 1


def test_list_documents(app_and_client):
    client, _ = app_and_client
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

    # Upload first
    files = {"file": ("sample.md", io.BytesIO(b"# Header\nContent here"), "text/markdown")}
    client.post("/documents", headers=headers, files=files)

    # List
    response = client.get("/documents", headers=headers)
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 1
    assert any(d["name"] == "sample.md" for d in docs)


def test_upload_empty_document(app_and_client):
    client, _ = app_and_client
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    response = client.post("/documents", headers=headers, files=files)
    assert response.status_code == 400


def test_upload_unsupported_format(app_and_client):
    client, _ = app_and_client
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

    files = {"file": ("malicious.exe", io.BytesIO(b"binarycontent"), "application/octet-stream")}
    response = client.post("/documents", headers=headers, files=files)
    assert response.status_code == 422


def test_delete_document(app_and_client):
    client, _ = app_and_client
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}

    # Upload
    files = {"file": ("to_delete.txt", io.BytesIO(b"Ephemeral text"), "text/plain")}
    upload_res = client.post("/documents", headers=headers, files=files)
    doc_id = upload_res.json()["id"]

    # Delete
    del_res = client.delete(f"/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json() == {"deleted": doc_id}

    # Verify deleted
    list_res = client.get("/documents", headers=headers)
    assert all(d["id"] != doc_id for d in list_res.json())
