from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_UPSTREAM_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"


@dataclass(frozen=True)
class CloudflareAccount:
    name: str
    account_id: str
    api_token: str
    upstream_base: str = DEFAULT_UPSTREAM_BASE

    def endpoint(self, path: str) -> str:
        base = self.upstream_base.format(account_id=self.account_id).rstrip("/")
        return f"{base}/{path.lstrip('/')}"


@dataclass(frozen=True)
class Settings:
    config_path: Path
    host: str
    port: int
    request_timeout_seconds: float
    max_attempts: int
    accounts: list[CloudflareAccount]


def load_settings(config_path: str | None = None) -> Settings:
    path = Path(config_path or os.getenv("GLMLLB_CONFIG", "config.json"))
    raw: dict[str, Any] = {}

    if path.exists():
        raw = json.loads(path.read_text())

    accounts_raw = raw.get("accounts") or _accounts_from_env()
    accounts = [
        CloudflareAccount(
            name=str(item.get("name") or item["account_id"]),
            account_id=str(item["account_id"]),
            api_token=str(item["api_token"]),
            upstream_base=str(item.get("upstream_base") or DEFAULT_UPSTREAM_BASE),
        )
        for item in accounts_raw
    ]

    return Settings(
        config_path=path,
        host=str(raw.get("host") or os.getenv("GLMLLB_HOST", "127.0.0.1")),
        port=int(raw.get("port") or os.getenv("GLMLLB_PORT", "2455")),
        request_timeout_seconds=float(raw.get("request_timeout_seconds") or os.getenv("GLMLLB_TIMEOUT", "120")),
        max_attempts=max(1, int(raw.get("max_attempts") or os.getenv("GLMLLB_MAX_ATTEMPTS", str(len(accounts))))),
        accounts=accounts,
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
