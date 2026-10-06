import os
from pathlib import Path

from app.core.config import Settings


MANAGED_KEYS = ("LLM_MODE", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY")


def persist_llm_settings(base_url: str, model: str, api_key: str, env_path: Path = Path(".env")) -> None:
    existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    replacements = {
        "LLM_MODE": "live",
        "LLM_BASE_URL": base_url,
        "LLM_MODEL": model,
        "LLM_API_KEY": api_key,
    }
    output: list[str] = []
    written: set[str] = set()
    for line in existing:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in replacements:
            output.append(f"{key}={replacements[key]}")
            written.add(key)
        else:
            output.append(line)
    for key in MANAGED_KEYS:
        if key not in written:
            output.append(f"{key}={replacements[key]}")
    temporary = env_path.with_suffix(".tmp")
    temporary.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    os.replace(temporary, env_path)


def apply_llm_settings(settings: Settings, base_url: str, model: str, api_key: str) -> None:
    settings.llm_mode = "live"
    settings.llm_base_url = base_url
    settings.llm_model = model
    settings.llm_api_key = api_key

