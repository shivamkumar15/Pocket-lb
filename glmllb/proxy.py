from __future__ import annotations

import itertools
import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from html import escape
from urllib.parse import parse_qs

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from glmllb.config import CloudflareAccount, Settings, load_settings


RETRY_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
}


class AccountPool:
    def __init__(self, accounts: list[CloudflareAccount]) -> None:
        self._accounts = accounts
        self._cursor = itertools.count()

    def next_attempts(self, max_attempts: int) -> list[CloudflareAccount]:
        attempts = min(max_attempts, len(self._accounts))
        start = next(self._cursor)
        return [self._accounts[(start + offset) % len(self._accounts)] for offset in range(attempts)]


class UsageTracker:
    def __init__(self, accounts: list[CloudflareAccount]) -> None:
        now = time.time()
        self._usage = {
            account.account_id: {
                "requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "unknown_token_responses": 0,
                "period_started_at": now,
                "last_used_at": None,
            }
            for account in accounts
        }

    def record(self, account: CloudflareAccount, payload: object | None) -> None:
        item = self._usage.setdefault(
            account.account_id,
            {
                "requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "unknown_token_responses": 0,
                "period_started_at": time.time(),
                "last_used_at": None,
            },
        )
        self._reset_if_needed(account, item)
        item["requests"] += 1
        item["last_used_at"] = time.time()

        usage = payload.get("usage") if isinstance(payload, dict) else None
        if not isinstance(usage, dict):
            item["unknown_token_responses"] += 1
            return

        item["prompt_tokens"] += _safe_int(usage.get("prompt_tokens"))
        item["completion_tokens"] += _safe_int(usage.get("completion_tokens"))
        item["total_tokens"] += _safe_int(usage.get("total_tokens"))

    def snapshot(self, account: CloudflareAccount) -> dict[str, object]:
        item = self._usage.setdefault(
            account.account_id,
            {
                "requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "unknown_token_responses": 0,
                "period_started_at": time.time(),
                "last_used_at": None,
            },
        )
        self._reset_if_needed(account, item)
        total_tokens = int(item["total_tokens"])
        remaining = None if account.token_limit is None else max(0, account.token_limit - total_tokens)
        reset_at = None
        if account.reset_period_hours:
            reset_at = float(item["period_started_at"]) + (account.reset_period_hours * 3600)
        return {
            **item,
            "remaining_tokens": remaining,
            "reset_at": reset_at,
        }

    def _reset_if_needed(self, account: CloudflareAccount, item: dict[str, object]) -> None:
        if not account.reset_period_hours:
            return
        reset_at = float(item["period_started_at"]) + (account.reset_period_hours * 3600)
        if time.time() < reset_at:
            return
        item.update(
            {
                "requests": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "unknown_token_responses": 0,
                "period_started_at": time.time(),
                "last_used_at": None,
            }
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    pool = AccountPool(settings.accounts)
    usage_tracker = UsageTracker(settings.accounts)
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    client: httpx.AsyncClient | None = None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        nonlocal client
        client = httpx.AsyncClient(timeout=timeout)
        try:
            yield
        finally:
            await client.aclose()

    app = FastAPI(title="glmllb", version="0.1.0", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> str:
        return _dashboard_html(settings, usage_tracker)

    @app.get("/setup", response_class=HTMLResponse)
    async def setup_form() -> str:
        return _setup_html(settings)

    @app.post("/setup", response_class=HTMLResponse)
    async def save_setup(request: Request) -> str:
        body = (await request.body()).decode()
        form = parse_qs(body, keep_blank_values=True)
        accounts = []

        account_count = max(1, _safe_int(_form_value(form, "account_count"), 1))
        for index in range(1, account_count + 1):
            account_id = _form_value(form, f"account_id_{index}")
            api_token = _form_value(form, f"api_token_{index}")
            name = _form_value(form, f"name_{index}") or f"cloudflare-{index}"
            token_limit = _form_value(form, f"token_limit_{index}")
            reset_period_hours = _form_value(form, f"reset_period_hours_{index}")
            if account_id or api_token:
                if not account_id or not api_token:
                    return _setup_html(settings, error=f"Account #{index} needs both account ID and API token.")
                account = {"name": name, "account_id": account_id, "api_token": api_token}
                if token_limit:
                    account["token_limit"] = int(token_limit)
                if reset_period_hours:
                    account["reset_period_hours"] = int(reset_period_hours)
                accounts.append(account)

        if not accounts:
            return _setup_html(settings, error="Add at least one Cloudflare account.")

        config = {
            "host": settings.host,
            "port": settings.port,
            "request_timeout_seconds": settings.request_timeout_seconds,
            "max_attempts": min(settings.max_attempts, len(accounts)) or 1,
            "accounts": accounts,
        }
        settings.config_path.write_text(json.dumps(config, indent=2) + "\n")
        return _setup_html(settings, saved=True)

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "ok": True,
            "accounts": [account.name for account in settings.accounts],
            "max_attempts": settings.max_attempts,
        }

    @app.get("/usage")
    async def usage() -> dict[str, object]:
        accounts = []
        for account in settings.accounts:
            item = usage_tracker.snapshot(account)
            accounts.append(
                {
                    "name": account.name,
                    "account_id": _mask_account_id(account.account_id),
                    "token_limit": account.token_limit,
                    "reset_period_hours": account.reset_period_hours,
                    **item,
                }
            )
        return {"accounts": accounts}

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def proxy(path: str, request: Request) -> Response:
        if client is None:
            return JSONResponse({"error": "Proxy client is not ready."}, status_code=503)
        if not settings.accounts:
            return JSONResponse(
                {"error": "No Cloudflare accounts configured.", "setup_url": "/setup"},
                status_code=428,
            )

        body = await request.body()
        incoming_headers = _forward_headers(request)
        last_response: httpx.Response | None = None
        last_error: Exception | None = None

        for account in pool.next_attempts(settings.max_attempts):
            headers = dict(incoming_headers)
            headers["authorization"] = f"Bearer {account.api_token}"
            headers["cf-aig-authorization"] = f"Bearer {account.api_token}"

            try:
                upstream_response = await client.send(
                    client.build_request(
                        request.method,
                        account.endpoint(path),
                        params=request.query_params,
                        content=body,
                        headers=headers,
                    ),
                    stream=True,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                continue

            if upstream_response.status_code not in RETRY_STATUSES:
                return await _tracked_response(upstream_response, account, usage_tracker)

            last_response = upstream_response
            await upstream_response.aclose()

        if last_response is not None:
            return JSONResponse(
                {"error": "All Cloudflare accounts failed or were rate limited.", "last_status": last_response.status_code},
                status_code=last_response.status_code,
            )

        return JSONResponse(
            {"error": "All Cloudflare accounts failed.", "detail": str(last_error) if last_error else None},
            status_code=502,
        )

    return app


def _forward_headers(request: Request) -> dict[str, str]:
    return {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() != "authorization"
    }


def _response_headers(response: httpx.Response, account_name: str) -> dict[str, str]:
    headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    headers["x-glmllb-account"] = account_name
    return headers


async def _tracked_response(response: httpx.Response, account: CloudflareAccount, usage_tracker: UsageTracker) -> Response:
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        usage_tracker.record(account, None)
        return _stream_response(response, account.name)

    body = await response.aread()
    payload = None
    if "json" in content_type:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None
    usage_tracker.record(account, payload)
    await response.aclose()
    return Response(
        content=body,
        status_code=response.status_code,
        headers=_response_headers(response, account.name),
        media_type=response.headers.get("content-type"),
    )


def _stream_response(response: httpx.Response, account_name: str) -> StreamingResponse:
    async def body() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()

    return StreamingResponse(
        body(),
        status_code=response.status_code,
        headers=_response_headers(response, account_name),
        media_type=response.headers.get("content-type"),
    )


def _dashboard_html(settings: Settings, usage_tracker: UsageTracker) -> str:
    base_url = f"http://{settings.host}:{settings.port}/v1"
    status_label = "Online" if settings.accounts else "Setup required"
    status_class = "status-ok" if settings.accounts else "status-warn"
    snapshots = [(account, usage_tracker.snapshot(account)) for account in settings.accounts]
    total_observed = sum(int(item["total_tokens"]) for _, item in snapshots)
    total_limit = sum(account.token_limit or 0 for account, _ in snapshots)
    total_remaining = None if total_limit == 0 else max(0, total_limit - total_observed)
    rows = "".join(
        f"""
        <div class="account-card">
          <div class="account-top">
            <div><b>{escape(account.name)}</b><code>{escape(_mask_account_id(account.account_id))}</code></div>
            <span>{_format_int(int(item['total_tokens']))} tokens</span>
          </div>
          <div class="meter"><i style="width: {_usage_percent(account, item)}%"></i></div>
          <div class="quota-grid">
            <span>Prompt <b>{_format_int(int(item['prompt_tokens']))}</b></span>
            <span>Completion <b>{_format_int(int(item['completion_tokens']))}</b></span>
            <span>Limit <b>{_format_optional_int(account.token_limit)}</b></span>
            <span>Remaining <b>{_format_optional_int(item['remaining_tokens'])}</b></span>
            <span>Requests <b>{_format_int(int(item['requests']))}</b></span>
            <span>Reset <b>{_format_reset(item['reset_at'])}</b></span>
          </div>
          <p class="hint">Unknown-token responses: {_format_int(int(item['unknown_token_responses']))}</p>
        </div>
        """
        for account, item in snapshots
    ) or "<p class=\"muted\">No Cloudflare accounts configured yet.</p>"

    return _codex_shell(
        title="GLM LLB",
        subtitle="API Load Balancer",
        body=f"""
        <div class="panel-head">
          <div>
            <h2>Dashboard</h2>
            <p class="muted">Local Cloudflare-compatible endpoint for OpenCode.</p>
          </div>
          <span class="status {status_class}">{status_label}</span>
        </div>
        <div class="stack">
          <label>OpenCode Base URL
            <div class="copyline"><code>{escape(base_url)}</code></div>
          </label>
          <div class="stats">
            <div><b>{len(settings.accounts)}</b><span>Accounts</span></div>
            <div><b>{_format_int(total_observed)}</b><span>Observed tokens</span></div>
            <div><b>{_format_optional_int(total_remaining)}</b><span>Remaining</span></div>
          </div>
          <p class="hint">Token counts are local observations from provider <code>usage</code> fields. Streaming responses or providers that omit usage are counted as unknown-token responses.</p>
          <div class="accounts">{rows}</div>
          <div class="actions">
            <a class="button" href="/setup">Setup Accounts</a>
            <a class="button secondary" href="/usage">Usage JSON</a>
          </div>
        </div>
        """,
    )


def _setup_html(settings: Settings, saved: bool = False, error: str | None = None) -> str:
    existing = settings.accounts or [CloudflareAccount(name="cloudflare-1", account_id="", api_token="")]
    account_rows = "".join(_account_setup_block(index, account) for index, account in enumerate(existing, start=1))
    notice = ""
    if saved:
        notice = "<div class=\"notice success\">Saved to local config.json. Restart glmllb, then open the dashboard.</div>"
    elif error:
        notice = f"<div class=\"notice error\">{escape(error)}</div>"

    return _codex_shell(
        title="GLM LLB",
        subtitle="API Load Balancer",
        body=f"""
        <h2>Setup</h2>
        <p class="muted">Add as many Cloudflare accounts as you want. Optional token limits and reset windows power the local quota dashboard.</p>
        {notice}
        <form method="post" action="/setup" class="stack" id="setup-form">
          <input type="hidden" name="account_count" id="account-count" value="{len(existing)}">
          <div id="account-list">{account_rows}</div>
          <button class="button secondary" type="button" id="add-account">Add Another Account</button>
          <button class="button" type="submit">Save Configuration</button>
        </form>
        <p class="footnote"><a href="/">Back to dashboard</a></p>
        <script>
          const list = document.getElementById('account-list');
          const count = document.getElementById('account-count');
          document.getElementById('add-account').addEventListener('click', () => {{
            const index = Number(count.value) + 1;
            count.value = String(index);
            list.insertAdjacentHTML('beforeend', `
              <details open>
                <summary>Cloudflare Account #${{index}}</summary>
                <div class="field-grid">
                  <label>Name <input name="name_${{index}}" value="cloudflare-${{index}}" autocomplete="off"></label>
                  <label>Account ID <input name="account_id_${{index}}" autocomplete="off" placeholder="Cloudflare account ID"></label>
                  <label>API Token <input name="api_token_${{index}}" type="password" autocomplete="off" placeholder="Cloudflare API token"></label>
                  <label>Token Limit <input name="token_limit_${{index}}" inputmode="numeric" autocomplete="off" placeholder="Optional, e.g. 10000000"></label>
                  <label>Reset Hours <input name="reset_period_hours_${{index}}" inputmode="numeric" autocomplete="off" placeholder="Optional, e.g. 24"></label>
                </div>
              </details>`);
          }});
        </script>
        """,
    )


def _account_setup_block(index: int, account: CloudflareAccount) -> str:
    token_limit = "" if account.token_limit is None else str(account.token_limit)
    reset_period_hours = "" if account.reset_period_hours is None else str(account.reset_period_hours)
    return f"""
    <details {'open' if index == 1 else ''}>
      <summary>Cloudflare Account #{index}</summary>
      <div class="field-grid">
        <label>Name <input name="name_{index}" value="{escape(account.name)}" autocomplete="off"></label>
        <label>Account ID <input name="account_id_{index}" value="{escape(account.account_id)}" autocomplete="off" placeholder="Cloudflare account ID"></label>
        <label>API Token <input name="api_token_{index}" value="{escape(account.api_token)}" type="password" autocomplete="off" placeholder="Cloudflare API token"></label>
        <label>Token Limit <input name="token_limit_{index}" value="{escape(token_limit)}" inputmode="numeric" autocomplete="off" placeholder="Optional, e.g. 10000000"></label>
        <label>Reset Hours <input name="reset_period_hours_{index}" value="{escape(reset_period_hours)}" inputmode="numeric" autocomplete="off" placeholder="Optional, e.g. 24"></label>
      </div>
    </details>
    """


def _codex_shell(title: str, subtitle: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: dark; --bg: #03060d; --panel: #0d121c; --panel-2: #111722; --line: #202a3b; --text: #e7edf7; --muted: #8b94a3; --blue: #5790ff; --blue-2: #2d6df6; --red: #ff5d6c; --green: #55d686; --orange: #f59e0b; }}
    * {{ box-sizing: border-box; }}
    html {{ min-height: 100%; background: var(--bg); }}
    body {{ margin: 0; min-height: 100vh; color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at 50% 42%, rgba(23, 42, 72, .54), transparent 30rem), radial-gradient(circle at 50% 120%, rgba(7, 28, 62, .52), transparent 28rem), linear-gradient(135deg, #050812 0%, #03060d 52%, #070a11 100%); }}
    body::before {{ content: ""; position: fixed; inset: 0; pointer-events: none; background: linear-gradient(rgba(255,255,255,.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.012) 1px, transparent 1px); background-size: 64px 64px; mask-image: radial-gradient(circle at center, black, transparent 72%); }}
    main {{ min-height: 100vh; display: grid; place-items: center; padding: 32px 16px; }}
    .wrap {{ width: min(720px, 100%); }}
    .brand {{ display: grid; justify-items: center; gap: 10px; margin-bottom: 32px; text-align: center; }}
    .logo {{ width: 64px; height: 64px; display: grid; place-items: center; border: 1px solid #1c3159; border-radius: 19px; background: linear-gradient(180deg, rgba(26,43,74,.58), rgba(8,13,23,.9)); box-shadow: inset 0 0 0 3px rgba(0,0,0,.32); }}
    .terminal {{ width: 31px; height: 31px; border: 3px solid var(--blue); border-radius: 50%; position: relative; }}
    .terminal::before {{ content: ">"; position: absolute; left: 6px; top: 3px; color: var(--blue); font: 800 16px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .terminal::after {{ content: ""; position: absolute; right: 7px; bottom: 8px; width: 7px; height: 2px; border-radius: 999px; background: var(--blue); }}
    h1 {{ margin: 0; font-size: 20px; line-height: 1.1; letter-spacing: -.02em; }}
    .subtitle {{ margin: 0; color: var(--muted); font-size: 14px; }}
    .card {{ border: 1px solid var(--line); border-radius: 17px; padding: 25px; background: linear-gradient(180deg, rgba(16, 23, 35, .94), rgba(10, 15, 24, .96)); }}
    h2 {{ margin: 0 0 10px; font-size: 17px; letter-spacing: -.02em; }}
    p {{ margin: 0; }}
    .muted {{ color: var(--muted); font-size: 14px; line-height: 1.55; }}
    .stack {{ display: grid; gap: 16px; margin-top: 20px; }}
    label {{ display: grid; gap: 8px; color: var(--text); font-size: 12px; font-weight: 700; }}
    input {{ width: 100%; height: 38px; border: 1px solid #293449; border-radius: 8px; padding: 0 12px; background: #121822; color: var(--text); font: 500 14px/1 inherit; outline: none; }}
    input:focus {{ border-color: var(--blue); box-shadow: 0 0 0 3px rgba(87, 144, 255, .14); }}
    input::placeholder {{ color: #798393; }}
    details {{ border: 1px solid #202a3b; border-radius: 11px; background: rgba(7, 11, 18, .38); overflow: hidden; }}
    summary {{ cursor: pointer; padding: 13px 14px; color: #d8e0ec; font-size: 13px; font-weight: 800; }}
    .field-grid {{ display: grid; gap: 12px; padding: 0 14px 14px; }}
    #account-list {{ display: grid; gap: 12px; }}
    .button {{ display: inline-flex; align-items: center; justify-content: center; min-height: 36px; border: 0; border-radius: 8px; padding: 0 14px; background: var(--blue); color: #061124; font-size: 14px; font-weight: 800; text-decoration: none; cursor: pointer; }}
    .button:hover {{ background: #69a0ff; }}
    .button.secondary {{ border: 1px solid #293449; background: #121822; color: var(--text); }}
    .notice {{ margin-top: 18px; padding: 12px 14px; border-radius: 9px; font-size: 13px; font-weight: 700; }}
    .success {{ border: 1px solid rgba(85,214,134,.32); background: rgba(85,214,134,.1); color: var(--green); }}
    .error {{ border: 1px solid rgba(255,93,108,.34); background: rgba(255,93,108,.12); color: var(--red); }}
    code {{ color: #dbe7ff; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; word-break: break-all; }}
    .copyline {{ display: flex; align-items: center; min-height: 38px; border: 1px solid #293449; border-radius: 8px; padding: 0 12px; background: #121822; }}
    .panel-head {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }}
    .status {{ border-radius: 999px; padding: 6px 9px; font-size: 12px; font-weight: 800; white-space: nowrap; }}
    .status-ok {{ color: var(--green); background: rgba(85,214,134,.1); }}
    .status-warn {{ color: var(--orange); background: rgba(245,158,11,.1); }}
    .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }}
    .stats div {{ border: 1px solid #202a3b; border-radius: 10px; padding: 10px; background: rgba(7,11,18,.38); }}
    .stats b {{ display: block; font-size: 18px; }}
    .stats span {{ color: var(--muted); font-size: 11px; }}
    .accounts {{ display: grid; gap: 8px; }}
    .account-row {{ display: flex; justify-content: space-between; gap: 12px; border: 1px solid #202a3b; border-radius: 10px; padding: 10px 12px; background: rgba(7,11,18,.38); font-size: 13px; }}
    .account-card {{ display: grid; gap: 12px; border: 1px solid #202a3b; border-radius: 12px; padding: 13px; background: rgba(7,11,18,.38); }}
    .account-top {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; font-size: 13px; }}
    .account-top div {{ display: grid; gap: 4px; }}
    .account-top span {{ color: #dbe7ff; font-weight: 800; white-space: nowrap; }}
    .meter {{ height: 7px; overflow: hidden; border-radius: 999px; background: #111827; }}
    .meter i {{ display: block; height: 100%; border-radius: inherit; background: var(--blue); }}
    .quota-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }}
    .quota-grid span {{ display: grid; gap: 3px; color: var(--muted); font-size: 11px; }}
    .quota-grid b {{ color: var(--text); font-size: 13px; }}
    .hint {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
    .actions {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .footnote {{ margin-top: 16px; color: var(--muted); font-size: 13px; text-align: center; }}
    a {{ color: #83aeff; }}
    @media (max-width: 560px) {{ .card {{ padding: 20px; }} .actions, .stats, .quota-grid {{ grid-template-columns: 1fr; }} .account-top {{ display: grid; }} }}
  </style>
</head>
<body>
  <main>
    <div class="wrap">
      <div class="brand">
        <div class="logo"><div class="terminal"></div></div>
        <div>
          <h1>{escape(title)}</h1>
          <p class="subtitle">{escape(subtitle)}</p>
        </div>
      </div>
      <div class="card">{body}</div>
    </div>
  </main>
</body>
</html>"""


def _form_value(form: dict[str, list[str]], key: str) -> str:
    values = form.get(key) or [""]
    return values[0].strip()


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _format_int(value: int) -> str:
    return f"{value:,}"


def _format_optional_int(value: object) -> str:
    if value is None:
        return "Not set"
    return _format_int(int(value))


def _format_reset(reset_at: object) -> str:
    if reset_at is None:
        return "Not set"
    seconds = max(0, int(float(reset_at) - time.time()))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _usage_percent(account: CloudflareAccount, item: dict[str, object]) -> int:
    if not account.token_limit:
        return 0
    return min(100, int((int(item["total_tokens"]) / account.token_limit) * 100))


def _mask_account_id(account_id: str) -> str:
    if len(account_id) <= 8:
        return account_id
    return f"{account_id[:4]}...{account_id[-4:]}"


def main() -> None:
    settings = load_settings()
    uvicorn.run("glmllb.proxy:create_app", host=settings.host, port=settings.port, factory=True)


if __name__ == "__main__":
    main()
