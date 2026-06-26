# glmllb

A local load-balancing proxy for [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) that exposes an OpenAI-compatible API. Round-robin across multiple Cloudflare accounts, auto-retry on rate limits, track token usage, and manage everything from a built-in web dashboard.

```text
OpenCode / Cline / Aider / any OpenAI-compatible client
  -> http://localhost:2456/v1
  -> glmllb proxy (round-robin + retry + usage tracking)
  -> Cloudflare Account #1
  -> Cloudflare Account #2
  -> Cloudflare Account #3
  -> ...
```

The proxy forwards local `/v1/*` requests to Cloudflare Workers AI's OpenAI-compatible path:

```text
https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/*
```

## Features

- **Multi-account load balancing** — round-robin requests across unlimited Cloudflare accounts.
- **Automatic failover** — retries the next account on `408`, `409`, `425`, `429`, `500`, `502`, `503`, and `504`.
- **Model mappings** — map standard model names (e.g. `gpt-4o`, `claude-3-5-sonnet`) to any Cloudflare Workers AI model. Configure in the Settings tab.
- **Streaming support** — preserves Server-Sent Events (SSE) streaming and parses token usage from stream chunks.
- **Token usage tracking** — records prompt, completion, and total tokens per account from both regular and streaming responses.
- **Web dashboard** — live view of accounts, quota usage, per-account token distribution, model mappings, and endpoint info.
- **Dark/light theme** — toggle in the dashboard; dark mode uses near-black surfaces.
- **Local-first security** — credentials are stored only in local `config.json` (git-ignored).
- **Docker support** — ships with a `Dockerfile` and `docker-compose.yml`.

## Quick Start

### Prerequisites

- Python 3.11+

### Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

### Run

```bash
glmllb
```

Then open the setup page in your browser:

```text
http://localhost:2456/setup
```

Enter your Cloudflare account IDs and API tokens. You can add as many accounts as you want. Optional token limits and reset windows can be saved per account so the dashboard can estimate remaining quota and reset timing.

Restart `glmllb` after saving to reload the new accounts.

### Docker

```bash
docker-compose up -d
```

The container exposes port `2456` and mounts your local `config.json`.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard (accounts, usage, quota, model mappings) |
| `/setup` | GET/POST | Browser-based account configuration |
| `/health` | GET | Health check JSON |
| `/usage` | GET | Token usage JSON (per-account stats) |
| `/v1/*` | POST | OpenAI-compatible proxy (chat completions, embeddings, etc.) |

Health check:

```bash
curl http://localhost:2456/health
```

Usage JSON:

```bash
curl http://localhost:2456/usage
```

## Using With AI Tools

Point any OpenAI-compatible tool at:

```text
Base URL: http://localhost:2456/v1
API key: any non-empty value (e.g. glmllb-local)
```

The local API key is not used for Cloudflare authentication. Cloudflare credentials come from `config.json` or the `CLOUDFLARE_ACCOUNTS` environment variable.

### Model Mappings

Set up model mappings in the **Settings** tab of the dashboard to translate standard model names to Cloudflare Workers AI models:

```text
gpt-4o          -> @cf/meta/llama-3.1-8b-instruct
gpt-4o-mini     -> @cf/meta/llama-3.1-8b-instruct
claude-3-5-sonnet -> @cf/meta/llama-3.1-8b-instruct
glm-5.2         -> @cf/zai-org/glm-5.2
```

You can also use Cloudflare model names directly (e.g. `@cf/zai-org/glm-5.2`).

### OpenCode

```bash
opencode --api-base http://localhost:2456/v1 --api-key dummy --model gpt-4o
```

### Cline / Continue / Aider / Roo Code

Choose the OpenAI-compatible/custom provider and set:

```text
Base URL: http://localhost:2456/v1
API key: glmllb-local
Model: gpt-4o (or any mapped model name)
```

### Claude Code

Claude Code uses the Anthropic Messages API (`/v1/messages`), which is not OpenAI-compatible. This proxy forwards `/v1/*` directly to Cloudflare Workers AI's OpenAI-compatible endpoint, so Claude Code is not supported without an Anthropic-to-OpenAI translation layer.

## Configuration

### config.json

Created by the setup page. Git-ignored so secrets stay local.

```json
{
  "host": "127.0.0.1",
  "port": 2456,
  "request_timeout_seconds": 120.0,
  "max_attempts": 3,
  "model_mapping": {
    "gpt-4o": "@cf/meta/llama-3.1-8b-instruct"
  },
  "accounts": [
    {
      "name": "account-1",
      "account_id": "your-account-id",
      "api_token": "your-api-token"
    }
  ]
}
```

### Environment Variables

Instead of `config.json`, you can configure accounts via environment:

```bash
export CLOUDFLARE_ACCOUNTS='account_id_1:token_1,account_id_2:token_2,account_id_3:token_3'
export GLMLLB_PORT=2456
glmllb
```

## Behavior

- Round-robins requests across configured accounts.
- Retries another account on `408`, `409`, `425`, `429`, `500`, `502`, `503`, and `504`.
- Preserves streaming responses (SSE) and extracts token usage from stream chunks.
- Adds `x-glmllb-account` header to responses so you can see which account handled a request.
- Token counts are local observations from provider `usage` fields. Non-streaming responses and streaming responses with usage data are tracked; providers that omit usage are counted as unknown-token responses.
- Keeps `config.json` git-ignored so secrets are never committed.

## Dashboard

The web dashboard at `http://localhost:2456/` provides:

- **Quota overview** — aggregate usage across all accounts with a progress meter and donut chart.
- **Account distribution** — per-account token usage breakdown.
- **Per-account cards** — individual account health, usage, and quota meters.
- **Model mappings** — view configured model name translations.
- **Endpoint info** — base URL, health, and usage JSON links.
- **Dark/light theme toggle** — dark mode uses deep near-black surfaces.

The dashboard auto-refreshes usage data from the backend.

## Project Structure

```text
glmllb/
├── glmllb/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py        # Settings dataclass, config loading
│   └── proxy.py         # FastAPI app, proxy logic, dashboard HTML
├── hud-dashboard/        # Standalone HUD-style React dashboard (optional)
├── config.example.json
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## License

See repository for license details.
