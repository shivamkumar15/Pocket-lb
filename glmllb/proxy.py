from __future__ import annotations

import itertools
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from html import escape

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


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    pool = AccountPool(settings.accounts)
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
        return _dashboard_html(settings)

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "ok": True,
            "accounts": [account.name for account in settings.accounts],
            "max_attempts": settings.max_attempts,
        }

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def proxy(path: str, request: Request) -> Response:
        if client is None:
            return JSONResponse({"error": "Proxy client is not ready."}, status_code=503)

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
                return _stream_response(upstream_response, account.name)

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


def _dashboard_html(settings: Settings) -> str:
    rows = "".join(
        f"""
        <tr>
          <td>{escape(account.name)}</td>
          <td><code>{escape(_mask_account_id(account.account_id))}</code></td>
          <td><code>{escape(account.upstream_base.format(account_id=account.account_id))}</code></td>
        </tr>
        """
        for account in settings.accounts
    )
    base_url = f"http://{settings.host}:{settings.port}/v1"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>glmllb</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #08090d;
      --panel: #11131a;
      --panel-strong: #181b25;
      --text: #f3f5f7;
      --muted: #9aa3b2;
      --line: #2a2f3c;
      --accent: #f2c14e;
      --green: #4ade80;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 20% 0%, rgba(242, 193, 78, 0.16), transparent 30rem),
        linear-gradient(145deg, #08090d 0%, #10131b 48%, #07080b 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 56px 0; }}
    .hero {{ display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 28px; align-items: stretch; }}
    .card {{
      border: 1px solid var(--line);
      background: rgba(17, 19, 26, 0.84);
      border-radius: 24px;
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
      backdrop-filter: blur(16px);
    }}
    .intro {{ padding: 40px; }}
    .eyebrow {{ color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: 0.18em; text-transform: uppercase; }}
    h1 {{ margin: 14px 0 16px; font-size: clamp(44px, 8vw, 92px); line-height: 0.9; letter-spacing: -0.08em; }}
    p {{ color: var(--muted); font-size: 17px; line-height: 1.7; margin: 0; }}
    .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 32px; }}
    .metric {{ padding: 18px; border: 1px solid var(--line); border-radius: 18px; background: rgba(255, 255, 255, 0.03); }}
    .metric strong {{ display: block; font-size: 28px; }}
    .metric span {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.12em; }}
    .status {{ padding: 28px; display: flex; flex-direction: column; justify-content: space-between; }}
    .status-pill {{ display: inline-flex; align-items: center; gap: 10px; width: fit-content; padding: 10px 14px; border: 1px solid rgba(74, 222, 128, 0.34); border-radius: 999px; color: var(--green); background: rgba(74, 222, 128, 0.08); font-weight: 700; }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 18px var(--green); }}
    code {{ color: #f8e9b0; font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.92em; }}
    pre {{ overflow-x: auto; margin: 18px 0 0; padding: 18px; border-radius: 18px; background: #050609; border: 1px solid var(--line); color: #d7dde8; }}
    section {{ margin-top: 24px; padding: 28px; }}
    h2 {{ margin: 0 0 16px; font-size: 22px; letter-spacing: -0.03em; }}
    table {{ width: 100%; border-collapse: collapse; overflow: hidden; }}
    th, td {{ padding: 14px 12px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; }}
    tr:last-child td {{ border-bottom: 0; }}
    .actions {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    .action {{ padding: 20px; border: 1px solid var(--line); border-radius: 18px; background: var(--panel-strong); }}
    .action b {{ display: block; margin-bottom: 8px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    @media (max-width: 820px) {{
      main {{ padding: 24px 0; }}
      .hero, .actions {{ grid-template-columns: 1fr; }}
      .intro {{ padding: 28px; }}
      .metrics {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="hero">
      <div class="card intro">
        <div class="eyebrow">Cloudflare account load balancer</div>
        <h1>glmllb</h1>
        <p>Local Cloudflare-compatible API proxy for OpenCode. Send requests to one local endpoint and let glmllb rotate across your configured Cloudflare accounts with retry failover.</p>
        <div class="metrics">
          <div class="metric"><strong>{len(settings.accounts)}</strong><span>accounts</span></div>
          <div class="metric"><strong>{settings.max_attempts}</strong><span>max attempts</span></div>
          <div class="metric"><strong>{settings.port}</strong><span>local port</span></div>
        </div>
      </div>
      <div class="card status">
        <div>
          <div class="status-pill"><span class="dot"></span>Proxy online</div>
          <pre>baseURL: {escape(base_url)}
health:  http://{escape(settings.host)}:{settings.port}/health</pre>
        </div>
        <p>Responses include <code>x-glmllb-account</code> so you can identify which Cloudflare account handled each request.</p>
      </div>
    </div>

    <section class="card">
      <h2>Configured Accounts</h2>
      <table>
        <thead><tr><th>Name</th><th>Account ID</th><th>Upstream</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>

    <section class="card">
      <h2>Quick Actions</h2>
      <div class="actions">
        <div class="action"><b>OpenCode URL</b><code>{escape(base_url)}</code></div>
        <div class="action"><b>Health JSON</b><a href="/health">/health</a></div>
        <div class="action"><b>Proxy Path</b><code>/v1/*</code></div>
      </div>
    </section>
  </main>
</body>
</html>"""


def _mask_account_id(account_id: str) -> str:
    if len(account_id) <= 8:
        return account_id
    return f"{account_id[:4]}...{account_id[-4:]}"


def main() -> None:
    settings = load_settings()
    uvicorn.run("glmllb.proxy:create_app", host=settings.host, port=settings.port, factory=True)


if __name__ == "__main__":
    main()
