# Zerops: environment-configured providers

The deployment defaults to server-key mode. No provider keys belong in Git or the browser. Router URLs and model names are independent environment settings; changing them requires restarting/redeploying the agent, not editing Python code.

## Existing deployment

1. On `uiagent`, add secret environment variables `OPENAI_API_KEY` and `TYPESAFE_API_KEY`. They may be different keys. Rotate any credentials previously posted in chat. Use the variables in `.env.server.example` for URL/model overrides. `OPENAI_BASE_URL` ends in `/v1`; `JEV_API_URL` is the full `/v1/systemone` URL.
2. On `web`, set `OIUI_AUTH_PASSWORD` as a secret (12+ characters). `OIUI_AUTH_USERNAME` defaults to `admin`. Do not reuse either provider key as the password.
3. Redeploy both services from the latest `main`. Wait for both to become healthy. Open the web HTTPS URL and authenticate with that username/password. There is no provider-key popup in server mode.
4. Test a plain-text question, a table, and an interactive calculator. Health endpoints verify liveness only. Custom answer models must support streamed function/tool calls and sufficiently long tool arguments. The router's Jev endpoint must support the app's `choice` question schema and return `answers.visualization` with `type`, `choice`, `confidence`, and `probabilities`. An urgency-only `noul` example is not proof of that compatibility.

## Settings

Agent: `PROVIDER_KEYS_MODE=server`, `LLM_PROVIDER=openai`, `OPENAI_BASE_URL`, `LLM_MODEL`, `OPENAI_API_KEY`, `JEV_API_URL`, `JEV_MODEL`, `TYPESAFE_API_KEY`.

Web: `PROVIDER_KEYS_MODE=server`, `LANGGRAPH_DEPLOYMENT_URL=http://uiagent:8123`, `OIUI_AUTH_USERNAME`, `OIUI_AUTH_PASSWORD`.

Normal Zerops variables in `zerops.yaml` supply the public router URLs/model names. Override them in Zerops when changing providers. Never store API keys in public frontend variables. Server mode disables visitor provider-key headers. The web proxy protects pages and API endpoints with HTTP Basic auth and fails closed if the password is missing/too short; only health and static assets are public. Keep uiagent private. Always access web over HTTPS.

For local development, put the agent settings in `apps/agent/.env` and web settings in `apps/app/.env.local`. The root example is a template, not an automatically loaded environment file. Both services must have matching `PROVIDER_KEYS_MODE` values. Provider settings are read on the server. The frontend receives only a boolean selecting server mode, not any provider URL or secret.

BYOK mode remains the stock alternative: set `PROVIDER_KEYS_MODE=byok` on both services, and visitors use official OpenAI/Jev endpoints with their own keys. Server-mode auth is not applied in BYOK mode.

Shared server mode is a single-owner deployment, not a multi-tenant authorization system. Agent checkpoints remain in memory and may be lost on restart. Authentication does not make sessions durable. No live router or Zerops smoke test is implied by the configuration.
