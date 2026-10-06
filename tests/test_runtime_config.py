from pathlib import Path

from app.services.runtime_config import persist_llm_settings


def test_runtime_configuration_updates_only_managed_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("APP_ENV=development\nADMIN_TOKEN=unchanged-token\nLLM_MODE=demo\n", encoding="utf-8")

    persist_llm_settings("http://127.0.0.1:11434/v1", "qwen3:8b", "local-key", env_file)

    content = env_file.read_text(encoding="utf-8")
    assert "APP_ENV=development" in content
    assert "ADMIN_TOKEN=unchanged-token" in content
    assert "LLM_MODE=live" in content
    assert "LLM_BASE_URL=http://127.0.0.1:11434/v1" in content
    assert "LLM_MODEL=qwen3:8b" in content
    assert "LLM_API_KEY=local-key" in content
