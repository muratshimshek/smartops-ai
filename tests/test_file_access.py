from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

ADMIN_HEADERS = {"X-Admin-Token": "test-admin-token-12345"}


def add_path(client: TestClient, root: Path, permission: str = "read") -> dict:
    response = client.post(
        "/api/v1/admin/paths",
        headers=ADMIN_HEADERS,
        json={"label": root.name, "root_path": str(root), "permission": permission},
    )
    assert response.status_code == 201
    return response.json()


def test_admin_routes_require_token(client: TestClient) -> None:
    assert client.get("/api/v1/admin/paths").status_code == 401


def test_adding_same_path_twice_is_idempotent(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "existing"
    root.mkdir()
    first = add_path(client, root)
    second = add_path(client, root)
    assert second["id"] == first["id"]


def test_index_and_search_only_allowed_path(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "contract.txt").write_text("ABC şirketi bakım sözleşmesi 2027 sonuna kadar geçerlidir.", encoding="utf-8")
    allowed = add_path(client, root)

    indexed = client.post(f"/api/v1/admin/paths/{allowed['id']}/index", headers=ADMIN_HEADERS)
    assert indexed.status_code == 200
    assert indexed.json()["indexed_files"] == 1

    search = client.post("/api/v1/files/search", json={"query": "bakım sözleşmesi"})
    assert search.status_code == 200
    assert search.json()[0]["file_name"] == "contract.txt"
    assert "2027" in search.json()[0]["excerpt"]
    opened = client.get(f"/api/v1/files/{search.json()[0]['indexed_file_id']}/content")
    assert opened.status_code == 200
    assert "2027" in opened.content.decode("utf-8")


def test_assistant_file_tool_returns_answer_and_source(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "finance"
    root.mkdir()
    (root / "policy.txt").write_text("Bakım dönemi 2028 yılının ilk çeyreğinde başlayacaktır.", encoding="utf-8")
    allowed = add_path(client, root)
    indexed = client.post(f"/api/v1/admin/paths/{allowed['id']}/index", headers=ADMIN_HEADERS)
    assert indexed.status_code == 200

    response = client.post("/api/v1/chat", json={"message": "/files bakım dönemi"})
    assert response.status_code == 200
    body = response.json()
    assert "2028" in body["response"]
    assert body["tools_used"] == ["search_allowed_files"]
    assert body["sources"][0]["file_name"] == "policy.txt"
    assert body["sources"][0]["indexed_file_id"]
    assert body["sources"][0]["directory_path"] == str(root.resolve())
    assert "Kaynak:" not in body["response"]
    assert str(root.resolve()) not in body["response"]


def test_excel_content_is_indexed_and_searchable(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "spreadsheets"
    root.mkdir()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Stok"
    sheet.append(["Hizmet", "Durum"])
    sheet.append(["Bakım sözleşmesi", "Aktif"])
    workbook.save(root / "services.xlsx")
    workbook.close()

    allowed = add_path(client, root)
    indexed = client.post(f"/api/v1/admin/paths/{allowed['id']}/index", headers=ADMIN_HEADERS)
    assert indexed.status_code == 200
    assert indexed.json()["indexed_files"] == 1

    search = client.post("/api/v1/files/search", json={"query": "bakım sözleşmesi"})
    assert search.status_code == 200
    assert search.json()[0]["file_name"] == "services.xlsx"
    assert "Aktif" in search.json()[0]["excerpt"]


def test_write_requires_permission_and_explicit_approval(client: TestClient, tmp_path: Path) -> None:
    read_root = tmp_path / "read-only"
    read_root.mkdir()
    read_allowed = add_path(client, read_root, "read")
    rejected = client.post("/api/v1/files/write-requests", json={
        "allowed_path_id": read_allowed["id"], "relative_path": "note.txt", "content": "test", "requested_by": "Ayşe"
    })
    assert rejected.status_code == 400

    write_root = tmp_path / "writable"
    write_root.mkdir()
    write_allowed = add_path(client, write_root, "read_write")
    proposed = client.post("/api/v1/files/write-requests", json={
        "allowed_path_id": write_allowed["id"], "relative_path": "note.txt", "content": "onaylı içerik", "requested_by": "Ayşe"
    })
    assert proposed.status_code == 202
    request_id = proposed.json()["id"]
    assert not (write_root / "note.txt").exists()

    approved = client.post(
        f"/api/v1/admin/write-requests/{request_id}/approve",
        headers=ADMIN_HEADERS,
        json={"actor": "Yönetici"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert (write_root / "note.txt").read_text(encoding="utf-8") == "onaylı içerik"


def test_write_rejects_path_traversal(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "safe"
    root.mkdir()
    allowed = add_path(client, root, "read_write")
    response = client.post("/api/v1/files/write-requests", json={
        "allowed_path_id": allowed["id"], "relative_path": "../escape.txt", "content": "blocked", "requested_by": "Ayşe"
    })
    assert response.status_code == 400
    assert not (tmp_path / "escape.txt").exists()
