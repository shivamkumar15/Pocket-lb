# glmllb

Local Cloudflare Workers AI account load balancer for OpenAI-compatible AI tools.

```text
OpenCode / OpenAI-compatible client
  -> http://localhost:2456/v1
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
```

Start the app, then open the browser setup page:

```bash
glmllb
```

```text
http://localhost:2456/setup
```

Enter as many Cloudflare account IDs and API tokens as you want in the setup page. Optional token limits and reset windows are saved with each account so the local dashboard can estimate remaining quota and reset timing.

Credentials are saved only to local `config.json`, which is ignored by git.

Restart `glmllb` after saving setup so the proxy reloads the new accounts.

## Run

```bash
glmllb
```

The default base URL is:

```text
http://localhost:2456/v1
```

Health check:

```bash
curl http://localhost:2456/health
```

Web dashboard:

```text
http://localhost:2456/
```

The dashboard shows configured accounts, the local OpenAI-compatible base URL, observed token usage, per-account token usage, estimated remaining quota, reset timing, and links to setup/usage endpoints.

Usage JSON:

```bash
curl http://localhost:2456/usage
```

Token counts are local observations from provider `usage` fields. Streaming responses or providers that omit usage are counted as unknown-token responses because the proxy cannot infer exact tokens without provider usage data.

## Environment-only config

Instead of `config.json`, you can configure accounts with:

```bash
export CLOUDFLARE_ACCOUNTS='account_id_1:token_1,account_id_2:token_2,account_id_3:token_3'
export GLMLLB_PORT=2456
glmllb
```

## Behavior

- Round-robins requests across configured accounts.
- Retries another account on `408`, `409`, `425`, `429`, `500`, `502`, `503`, and `504`.
- Preserves streaming responses.
- Adds `x-glmllb-account` to responses so you can see which account handled a request.
- Keeps `config.json` ignored so secrets are not committed by accident.

## Using With AI Tools

Use glmllb with tools that can talk to an OpenAI-compatible API and let you set a custom base URL.

```text
Base URL: http://localhost:2456/v1
API key: any non-empty value if the client requires one
Model: You can now use standard names like `gpt-4o` or `claude-3-5-sonnet-20241022` if you set up Model Mappings in the Settings tab, or you can use Cloudflare model names directly.
```

The local API key is not used for Cloudflare authentication. Cloudflare credentials come from `config.json` or `CLOUDFLARE_ACCOUNTS`.

### OpenCode

Point OpenCode at:

```text
baseURL: http://localhost:2456/v1
```

Because you can now set up **Model Mappings** in the Settings tab, you can use standard model names in OpenCode:

```bash
opencode --api-base http://localhost:2456/v1 --api-key dummy --model gpt-4o
```

(The proxy will automatically translate `gpt-4o` to your chosen Cloudflare model, like `@cf/meta/llama-3.1-8b-instruct`).

### Other OpenAI-Compatible Tools

For tools such as Aider, Continue, Cline, Roo Code, or editors with a generic OpenAI-compatible provider, choose the OpenAI-compatible/custom provider and set the base URL to:

```text
http://localhost:2456/v1
```

If the tool requires an API key, use a placeholder value such as `glmllb-local`.

### Claude Code

Claude Code does not use the OpenAI-compatible chat completions API by default. It normally sends Anthropic Messages API requests to `/v1/messages`.

This proxy currently forwards `/v1/*` directly to Cloudflare Workers AI's OpenAI-compatible endpoint, so Claude Code cannot be pointed at `http://localhost:2456` unless an Anthropic-to-OpenAI translation layer is added first.

For Claude Code support, glmllb would need an Anthropic-compatible adapter that accepts Claude Code's `/v1/messages` requests, converts them to OpenAI-compatible chat completions for Cloudflare Workers AI, then converts the response back to Anthropic's response shape.
