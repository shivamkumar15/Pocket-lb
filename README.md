# Pocket-lb

A local load-balancing proxy for [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) that exposes an OpenAI-compatible API. Round-robin across multiple Cloudflare accounts, auto-retry on rate limits, track token usage, and manage everything from a built-in web dashboard.

```text
OpenCode / Cline / Aider / any OpenAI-compatible client
  -> http://localhost:2456/v1
  -> Pocket-lb proxy (round-robin + retry + usage tracking)
  -> Cloudflare Account #1
  -> Cloudflare Account #2
  -> Cloudflare Account #3
  -> ...
```

## Screenshots <img width="1320" height="824" alt="2026-07-02-212503" src="https://github.com/user-attachments/assets/30a1f63e-f3ca-4fe7-b464-6fe9241a2521" />
<img width="1842" height="887" alt="2026-07-02-210831" src="https://github.com/user-attachments/assets/d2ae3c45-7931-45bb-9e1a-3ca1cdea2c00" />
<img width="1866" height="933" alt="2026-07-02-204911" src="https://github.com/user-attachments/assets/8ad14e61-5adf-403f-94ed-41b76fdfaadd" />


The proxy forwards local `/v1/*` requests to Cloudflare Workers AI's OpenAI-compatible path:

```text
https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/*
```

## Features

- **Multi-account load balancing** — round-robin requests across unlimited Cloudflare accounts.
- **Automatic failover** — tries the next account on `400`, `401`, `403`, `404`, `408`, `409`, `410`, `425`, `429`, `500`, `502`, `503`, and `504`, up to `max_attempts` accounts per request. Accounts that return `429` are backed off (honors `Retry-After`, default 60s) and quota-exhausted accounts are skipped.
- **Model mappings** — 50+ friendly aliases (e.g. `kimi-k2.7`, `glm-5.2`, `gpt-4o`) mapped to Cloudflare Workers AI models. Full `@cf/...` IDs work directly. View mappings in the Settings tab; edit them in `config.json`.
- **Streaming support** — preserves Server-Sent Events (SSE) streaming and parses token usage from stream chunks.
- **Token usage tracking** — records prompt, completion, and total tokens per account from both regular and streaming responses. Streams that carry no usage data are counted as unknown-token responses so request totals stay accurate.
- **Web dashboard** — live per-account status badges (`Active` / `Rate limited` / `Error N` / `Unreachable` / `Idle`), token distribution, request log with per-attempt breakdown, model mappings, and endpoint info. Auto-refreshes every 5s.
- **Failure transparency** — when all accounts fail, the response includes the upstream error (`upstream_detail`) instead of a generic message.
- **Dark/light theme** — toggle in the dashboard; dark mode uses near-black surfaces.
- **Local-first security** — credentials are stored only in local `config.json` (git-ignored).
- **Docker support** — ships with a `Dockerfile` and `docker-compose.yml`.

## Installation & Setup Guide

Follow these steps to get Pocket-lb running locally.

### Method 1: Local Python Installation

**Step 1: Clone the repository**
```bash
git clone https://github.com/shivamkumar15/Pocket-lb.git
cd Pocket-lb
```

**Step 2: Create a virtual environment**
Ensure you have Python 3.11 or newer installed.
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

**Step 3: Install the package**
```bash
pip install -e .
```

**Step 4: Start the server**
```bash
pocket-lb
```

**Step 5: Configure your Cloudflare accounts**
1. Open your browser and navigate to [http://localhost:2456/setup](http://localhost:2456/setup).
2. Enter your Cloudflare Account ID and API Token. You can generate an API token from your Cloudflare dashboard (ensure it has "Workers AI" permissions).
3. *(Optional)* Set token limits and reset windows to track your quota.
4. Click "Save". This securely writes a local `config.json` file and applies immediately — no restart needed (restart is only required if you edit `config.json` by hand).

### Method 2: Docker Setup

If you prefer using Docker, you can run Pocket-lb without installing Python dependencies.

**Step 1: Create a configuration file**
First, create an empty `config.json` file in the root directory (this allows Docker to mount the file instead of creating a directory):
```bash
echo "{}" > config.json
```

**Step 2: Start the container**
```bash
docker-compose up -d
```

**Step 3: Configure your accounts**
Visit [http://localhost:2456/setup](http://localhost:2456/setup) in your browser, add your Cloudflare credentials, and save. Changes apply immediately — no restart needed.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard (accounts, usage, quota, model mappings) |
| `/setup` | GET | Redirects to the dashboard Settings tab (`/?tab=settings`) |
| `/setup` | POST | Save accounts from the dashboard form (applies immediately) |
| `/health` | GET | Health check JSON |
| `/usage` | GET | Token usage JSON (per-account stats incl. `rate_limited`, plus request log) |
| `/v1/models` | GET | OpenAI-compatible model list (aliases + live Cloudflare catalog, cached 10 min) |
| `/v1/*` | ANY | OpenAI-compatible proxy (chat completions, embeddings, etc.) |

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
API key: any non-empty value (e.g. pocket-lb-local)
```

The local API key is not used for Cloudflare authentication. Cloudflare credentials come from `config.json` or the `CLOUDFLARE_ACCOUNTS` environment variable.

### Model Mappings

Set up model mappings in the **Settings** tab of the dashboard to translate standard model names to Cloudflare Workers AI models.
All Text Generation + Text Embeddings models in the Workers AI free allocation (10,000 Neurons/day, shared) are pre-mapped with friendly aliases — verified against the live catalog. You can also use any full Cloudflare model ID directly (e.g. `@cf/zai-org/glm-5.2`).

```text
# Generic OpenAI / Claude compatibility
gpt-4o              -> @cf/meta/llama-3.1-8b-instruct-fp8
gpt-4o-mini         -> @cf/meta/llama-3.2-3b-instruct
gpt-4.1             -> @cf/openai/gpt-oss-120b
gpt-4.1-mini        -> @cf/openai/gpt-oss-20b
claude-3-5-sonnet   -> @cf/mistralai/mistral-small-3.1-24b-instruct

# Kimi / GLM (coding)
kimi-k2.7-code      -> @cf/moonshotai/kimi-k2.7-code
kimi-k2.6           -> @cf/moonshotai/kimi-k2.6
glm-5.2             -> @cf/zai-org/glm-5.2
glm-5.3             -> @cf/zai-org/glm-5.3
glm-5.3-flash       -> @cf/zai-org/glm-5.3-flash
glm-4.7-flash       -> @cf/zai-org/glm-4.7-flash

# OpenAI open-weights / DeepSeek / Qwen
gpt-oss-120b        -> @cf/openai/gpt-oss-120b
gpt-oss-20b         -> @cf/openai/gpt-oss-20b
deepseek-v4-pro     -> @cf/deepseek-ai/deepseek-v4-pro-0813
deepseek-v4-flash   -> @cf/deepseek-ai/deepseek-v4-flash-0731
qwen2.5-coder-32b   -> @cf/qwen/qwen2.5-coder-32b-instruct
qwen3-30b           -> @cf/qwen/qwen3-30b-a3b-fp8
qwq-32b             -> @cf/qwen/qwq-32b

# Llama / Gemma / Mistral / others
llama-3.3-70b       -> @cf/meta/llama-3.3-70b-instruct-fp8-fast
llama-4-scout       -> @cf/meta/llama-4-scout-17b-16e-instruct
mistral-small-3.1   -> @cf/mistralai/mistral-small-3.1-24b-instruct
gemma-4-26b         -> @cf/google/gemma-4-26b-a4b-it
nemotron-120b       -> @cf/nvidia/nemotron-3-120b-a12b
...plus every other free chat + embedding model (see config.example.json)
```

### OpenCode

```bash
opencode --api-base http://localhost:2456/v1 --api-key dummy --model gpt-4o
```

### Cline / Continue / Aider / Roo Code

Choose the OpenAI-compatible/custom provider and set:

```text
Base URL: http://localhost:2456/v1
API key: pocket-lb-local
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
    "gpt-4o": "@cf/meta/llama-3.1-8b-instruct-fp8",
    "kimi-k2.7-code": "@cf/moonshotai/kimi-k2.7-code",
    "glm-5.2": "@cf/zai-org/glm-5.2"
  },
  "accounts": [
    {
      "name": "account-1",
      "account_id": "your-account-id",
      "api_token": "your-api-token",
      "token_limit": 10000000,
      "reset_period_hours": 24
    }
  ]
}
```

`token_limit` / `reset_period_hours` are optional per-account quota settings (also editable in the dashboard Settings tab). Accounts over their limit are skipped until the window resets.

### Environment Variables

`config.json` values can be overridden (or accounts supplied entirely) via environment:

```bash
export CLOUDFLARE_ACCOUNTS='account_id_1:token_1,account_id_2:token_2,account_id_3:token_3'
export POCKET_LB_CONFIG=config.json   # config file path
export POCKET_LB_HOST=127.0.0.1
export POCKET_LB_PORT=2456
export POCKET_LB_TIMEOUT=120          # upstream request timeout, seconds
export POCKET_LB_MAX_ATTEMPTS=3       # accounts tried per request
pocket-lb
```

## Behavior

- Round-robins requests across configured accounts (skips rate-limited and quota-exhausted ones).
- Tries up to `max_attempts` accounts per request, failing over on `400`, `401`, `403`, `404`, `408`, `409`, `410`, `425`, `429`, `500`, `502`, `503`, and `504`. `429` responses back off that account (honors `Retry-After`, default 60s).
- Preserves streaming responses (SSE) and extracts token usage from stream chunks; streams without usage data are counted as unknown-token responses.
- Adds `x-pocket-lb-account` header to responses so you can see which account handled a request.
- Failed-after-all-accounts responses include the upstream error as `upstream_detail` with `last_status`.
- Token counts are local observations from provider `usage` fields, persisted in `state.json`; the request log persists in `request_log.json`.
- Keeps `config.json` git-ignored so secrets are never committed.

## Dashboard

The web dashboard at `http://localhost:2456/` provides:

- **Live account status** — per-account badges derived from real recent attempts and rate-limit state (`Active` / `Rate limited` / `Error N` / `Unreachable` / `Idle`).
- **Quota overview** — aggregate usage with a gauge (shows `No quota set` when no limits are configured).
- **Account distribution** — per-account token usage breakdown bars.
- **Request log** — recent proxied requests with model, mapped model, duration, handling account, and per-attempt `account:status` trail.
- **Per-account cards** — usage, quota meters, request counts, and last-used timestamps.
- **Model mappings** — view configured model name translations.
- **Endpoint info** — base URL with copy button, host/port/retry/timeout summary, health and usage JSON links.
- **Settings tab** — add/edit accounts (ID, token, optional quota limit + reset window) and save without restarting.
- **Dark/light theme toggle** — dark mode uses deep near-black surfaces.

The dashboard auto-refreshes usage data from `/usage` every 5 seconds.

## Project Structure

```text
Pocket-lb/
├── pocket_lb/
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

