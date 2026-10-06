from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_web_interface(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "SmartOps AI" in response.text


def test_analysis_returns_valid_structured_output(client: TestClient) -> None:
    response = client.post("/api/v1/analyze", json={"issue": "A user cannot access a shared folder after changing departments."})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "other"
    assert body["severity"] in {"low", "medium", "high", "critical"}
    assert body["troubleshooting_steps"]
    assert "Demo modu" in body["probable_causes"][0]


def test_invalid_input(client: TestClient) -> None:
    assert client.post("/api/v1/analyze", json={"issue": "x"}).status_code == 422
    assert client.post("/api/v1/chat", json={"message": ""}).status_code == 422


def test_conversation_persistence_and_delete(client: TestClient) -> None:
    created = client.post("/api/v1/chat", json={"message": "/guide access"})
    assert created.status_code == 200
    conversation_id = created.json()["conversation_id"]
    assert created.json()["tools_used"] == ["get_troubleshooting_guide"]

    continued = client.post("/api/v1/chat", json={"conversation_id": conversation_id, "message": "What should I verify first?"})
    assert continued.status_code == 200

    fetched = client.get(f"/api/v1/conversations/{conversation_id}")
    assert fetched.status_code == 200
    assert [m["role"] for m in fetched.json()["messages"]] == ["user", "assistant", "user", "assistant"]

    assert client.delete(f"/api/v1/conversations/{conversation_id}").status_code == 204
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404


def test_demo_chat_is_explicit_about_not_understanding_natural_language(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": "Telefonum çekmiyor"})
    assert response.status_code == 200
    assert "Demo modu doğal dili analiz etmez" in response.json()["response"]


def test_tools_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    assert {tool["name"] for tool in response.json()} == {"search_knowledge_base", "check_service_status", "get_troubleshooting_guide", "search_allowed_files"}


def test_llm_status_does_not_expose_credentials(client: TestClient) -> None:
    response = client.get("/api/v1/admin/llm/status", headers={"X-Admin-Token": "test-admin-token-12345"})
    assert response.status_code == 200
    assert "api_key" not in response.json()
    assert response.json()["base_url"] == "http://127.0.0.1:11434/v1"

