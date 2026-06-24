# glmllb

Local Cloudflare Workers AI account load balancer for clients such as OpenCode.

```text
OpenCode
  -> http://localhost:2455/v1
  -> glmllb Cloudflare proxy
  -> Cloudflare Account #1
  -> Cloudflare Account #2
  -> Cloudflare Account #3
```

The proxy forwards local `/v1/*` requests to Cloudflare Workers AI's OpenAI-compatible path:

```text
https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/*
```

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
cp config.example.json config.json
```

Edit `config.json` with each Cloudflare account ID and API token.

## Run

```bash
glmllb
```

The default base URL is:

```text
http://localhost:2455/v1
```

Health check:

```bash
curl http://localhost:2455/health
```

Web dashboard:

```text
http://localhost:2455/
```

The dashboard shows configured accounts, the local OpenCode base URL, retry settings, and a link to the health endpoint.

## Environment-only config

Instead of `config.json`, you can configure accounts with:

```bash
export CLOUDFLARE_ACCOUNTS='account_id_1:token_1,account_id_2:token_2,account_id_3:token_3'
export GLMLLB_PORT=2455
glmllb
```

## Behavior

- Round-robins requests across configured accounts.
- Retries another account on `408`, `409`, `425`, `429`, `500`, `502`, `503`, and `504`.
- Preserves streaming responses.
- Adds `x-glmllb-account` to responses so you can see which account handled a request.
- Keeps `config.json` ignored so secrets are not committed by accident.

## OpenCode Provider

Point OpenCode at:

```text
baseURL: http://localhost:2455/v1
```

Use the Cloudflare model names you normally send to Workers AI, for example:

```text
@cf/meta/llama-3.1-8b-instruct
```
# glmllb
