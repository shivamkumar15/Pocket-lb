from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_UPSTREAM_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"

# All Text Generation + Text Embeddings models available on the Workers AI
# free allocation (10,000 Neurons/day, shared across models). Verified against
# the live `ai/models/search` catalog. Keys are friendly aliases accepted by
# OpenAI-compatible clients; values are the canonical `@cf/...` model IDs.
# Full `@cf/...` IDs also work directly without a mapping entry.
DEFAULT_MODEL_MAPPING: dict[str, str] = {
    # --- Generic OpenAI / Claude compatibility aliases (point at valid models) ---
    "gpt-4o": "@cf/meta/llama-3.1-8b-instruct-fp8",
    "gpt-4o-mini": "@cf/meta/llama-3.2-3b-instruct",
    "gpt-4.1": "@cf/openai/gpt-oss-120b",
    "gpt-4.1-mini": "@cf/openai/gpt-oss-20b",
    "claude-3-5-sonnet-20241022": "@cf/mistralai/mistral-small-3.1-24b-instruct",
    "claude-3-5-sonnet": "@cf/mistralai/mistral-small-3.1-24b-instruct",
    "claude-3-haiku": "@cf/meta/llama-3.2-3b-instruct",
    # --- Moonshot AI Kimi ---
    "kimi-k2.7-code": "@cf/moonshotai/kimi-k2.7-code",
    "kimi-k2.7": "@cf/moonshotai/kimi-k2.7-code",
    "kimi-k2.6": "@cf/moonshotai/kimi-k2.6",
    # --- Zhipu GLM ---
    "glm-4.7-flash": "@cf/zai-org/glm-4.7-flash",
    "glm5.2": "@cf/zai-org/glm-5.2",
    "glm-5.2": "@cf/zai-org/glm-5.2",
    "glm-5.3": "@cf/zai-org/glm-5.3",
    "glm-5.3-flash": "@cf/zai-org/glm-5.3-flash",
    # --- OpenAI open-weights ---
    "gpt-oss-120b": "@cf/openai/gpt-oss-120b",
    "gpt-oss-20b": "@cf/openai/gpt-oss-20b",
    # --- DeepSeek ---
    "deepseek-r1-distill-qwen-32b": "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
    "deepseek-r1-32b": "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
    "deepseek-v4-flash": "@cf/deepseek-ai/deepseek-v4-flash-0731",
    "deepseek-v4-pro": "@cf/deepseek-ai/deepseek-v4-pro-0813",
    # --- Meta Llama ---
    "llama-2-7b-chat": "@cf/meta-llama/llama-2-7b-chat-hf-lora",
    "llama-3.1-8b": "@cf/meta/llama-3.1-8b-instruct-fp8",
    "llama-3.1-8b-instruct": "@cf/meta/llama-3.1-8b-instruct-fp8",
    "llama-3.2-1b": "@cf/meta/llama-3.2-1b-instruct",
    "llama-3.2-1b-instruct": "@cf/meta/llama-3.2-1b-instruct",
    "llama-3.2-3b": "@cf/meta/llama-3.2-3b-instruct",
    "llama-3.2-3b-instruct": "@cf/meta/llama-3.2-3b-instruct",
    "llama-3.2-11b-vision": "@cf/meta/llama-3.2-11b-vision-instruct",
    "llama-3.3-70b": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "llama-3.3-70b-instruct": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "llama-4-scout": "@cf/meta/llama-4-scout-17b-16e-instruct",
    "llama-guard-3-8b": "@cf/meta/llama-guard-3-8b",
    # --- Google Gemma ---
    "gemma-2b-it": "@cf/google/gemma-2b-it-lora",
    "gemma-7b-it": "@cf/google/gemma-7b-it-lora",
    "gemma-4-26b": "@cf/google/gemma-4-26b-a4b-it",
    "sea-lion-27b": "@cf/aisingapore/gemma-sea-lion-v4-27b-it",
    # --- Qwen ---
    "qwen2.5-coder-32b": "@cf/qwen/qwen2.5-coder-32b-instruct",
    "qwen3-30b": "@cf/qwen/qwen3-30b-a3b-fp8",
    "qwen3.8-27b": "@cf/qwen/qwen3.8-27b",
    "qwq-32b": "@cf/qwen/qwq-32b",
    # --- Mistral ---
    "mistral-7b-instruct": "@cf/mistral/mistral-7b-instruct-v0.2-lora",
    "mistral-small-3.1": "@cf/mistralai/mistral-small-3.1-24b-instruct",
    # --- Others (chat) ---
    "granite-4-micro": "@cf/ibm-granite/granite-4.0-h-micro",
    "nemotron-120b": "@cf/nvidia/nemotron-3-120b-a12b",
    # --- Embeddings (for /v1/embeddings) ---
    "bge-small": "@cf/baai/bge-small-en-v1.5",
    "bge-base": "@cf/baai/bge-base-en-v1.5",
    "bge-large": "@cf/baai/bge-large-en-v1.5",
    "bge-m3": "@cf/baai/bge-m3",
    "embeddinggemma": "@cf/google/embeddinggemma-300m",
    "plamo-embedding-1b": "@cf/pfnet/plamo-embedding-1b",
    "qwen3-embedding-0.6b": "@cf/qwen/qwen3-embedding-0.6b",
    "text-embedding-ada-002": "@cf/baai/bge-large-en-v1.5",
    "text-embedding-3-small": "@cf/baai/bge-small-en-v1.5",
}


@dataclass(frozen=True)
class CloudflareAccount:
    name: str
    account_id: str
    api_token: str
    token_limit: int | None = None
    reset_period_hours: int | None = None
    upstream_base: str = DEFAULT_UPSTREAM_BASE

    def endpoint(self, path: str) -> str:
        base = self.upstream_base.format(account_id=self.account_id).rstrip("/")
        return f"{base}/{path.lstrip('/')}"


@dataclass
class Settings:
    config_path: Path
    host: str
    port: int
    request_timeout_seconds: float
    max_attempts: int
    accounts: list[CloudflareAccount]
    model_mapping: dict[str, str]


def load_settings(config_path: str | None = None) -> Settings:
    path = Path(config_path or os.getenv("POCKET_LB_CONFIG", "config.json"))
    raw: dict[str, Any] = {}

    if path.exists():
        raw = json.loads(path.read_text())

    accounts_raw = raw.get("accounts") or _accounts_from_env()
    accounts = [
        CloudflareAccount(
            name=str(item.get("name") or item["account_id"]),
            account_id=str(item["account_id"]),
            api_token=str(item["api_token"]),
            token_limit=_optional_int(item.get("token_limit")),
            reset_period_hours=_optional_int(item.get("reset_period_hours")),
            upstream_base=str(item.get("upstream_base") or DEFAULT_UPSTREAM_BASE),
        )
        for item in accounts_raw
    ]

    return Settings(
        config_path=path,
        host=str(os.getenv("POCKET_LB_HOST") or raw.get("host") or "127.0.0.1"),
        port=int(os.getenv("POCKET_LB_PORT") or raw.get("port") or "2456"),
        request_timeout_seconds=float(os.getenv("POCKET_LB_TIMEOUT") or raw.get("request_timeout_seconds") or "120"),
        max_attempts=max(1, int(os.getenv("POCKET_LB_MAX_ATTEMPTS") or raw.get("max_attempts") or str(len(accounts)))),
        accounts=accounts,
        model_mapping=dict(raw.get("model_mapping") or dict(DEFAULT_MODEL_MAPPING)),
    )


def _accounts_from_env() -> list[dict[str, str]]:
    value = os.getenv("CLOUDFLARE_ACCOUNTS", "").strip()
    if not value:
        return []

    accounts: list[dict[str, str]] = []
    for index, pair in enumerate(value.split(","), start=1):
        account_id, sep, api_token = pair.partition(":")
        if not sep or not account_id.strip() or not api_token.strip():
            raise RuntimeError("CLOUDFLARE_ACCOUNTS entries must be account_id:api_token pairs.")
        accounts.append(
            {
                "name": f"cf-{index}",
                "account_id": account_id.strip(),
                "api_token": api_token.strip(),
            }
        )
    return accounts


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
