# ClawHub Publish Pack

Use this pack to publish and support FlowGate as an OpenClaw custom provider for any user.

## Core Differentiator: OpenClaw-Native Event + Domain Routing

FlowGate does not only proxy chat completions. It understands OpenClaw-native routing signals and applies domain/channel-specific model routing.

- Reads `metadata.method` and `metadata.event` (plus compatible tags/flags).
- Detects domain/category/channel hints from OpenClaw payload metadata.
- Applies domain-specific drafter/verifier model pairs and thresholds.
- Supports channel routing for low-value operational events to cheaper models.

Minimal payload example (OpenClaw -> FlowGate):

```json
{
  "model": "flowgate",
  "messages": [{"role": "user", "content": "status ping"}],
  "metadata": {
    "method": "heartbeat",
    "event": "cron",
    "channel": "heartbeat"
  }
}
```

Result:

- operational events can route to cheap channel models
- code/reasoning/creative/user requests can route to domain-optimized cascades
- behavior works with Anthropic-only, OpenAI-only, and mixed presets

## Required Metadata

- `folder`: `flowgate`
- `slug`: `flowgate`
- `display_name`: `FlowGate: Cost + Latency Reduction`
- `source_url`: `https://github.com/oTheShyo/flowgate`
- `homepage_url`: `https://github.com/oTheShyo/flowgate/blob/main/docs/guides/openclaw_provider.md`

## Credentials To Declare In Listing

- `OPENAI_API_KEY` (required when using OpenAI models/preset)
- `ANTHROPIC_API_KEY` (required when using Anthropic models/preset)
- `FLOWGATE_AUTH_TOKEN` (recommended in production; maps to server `--auth-token`)
- `FLOWGATE_STATS_AUTH_TOKEN` (optional separate stats token; maps to server `--stats-auth-token`)

Do not leave credential requirements empty in listing metadata.
Use strong random token values in production (examples in this file are placeholders).

## Upload Folder

Upload this folder to ClawHub:

- `flowgate/` (the skill folder containing `SKILL.md`)

Minimum files included:

- `SKILL.md`
- `agents/openai.yaml`
- `references/clawhub_publish_pack.md`
- `references/market_positioning.md`

## 1) Install FlowGate

Fastest base setup (OpenClaw integration extras):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade "flowgate[openclaw]>=0.7,<0.8"
python -m pip show flowgate
python -m pip download --no-deps "flowgate[openclaw]>=0.7,<0.8" -d /tmp/flowgate_pkg
python -m pip hash /tmp/flowgate_pkg/flowgate-*.whl
```

Quick provider variants:

```bash
# Anthropic-only preset users
python -m pip install --upgrade "flowgate[openclaw,anthropic]>=0.7,<0.8"

# OpenAI-only preset users
python -m pip install --upgrade "flowgate[openclaw,openai]>=0.7,<0.8"

# Mixed preset users (OpenAI + Anthropic + common providers)
python -m pip install --upgrade "flowgate[openclaw,providers]>=0.7,<0.8"
```

## 2) Pick A Preset Config (All 3)

Preset files:

- `examples/configs/anthropic-only.yaml`
- `examples/configs/openai-only.yaml`
- `examples/configs/mixed-anthropic-openai.yaml`

Notes:

- Anthropic-only: lower-cost Anthropic drafter -> stronger Anthropic verifier.
- OpenAI-only: current main uses `gpt-5-mini` drafter -> `gpt-5` verifier.
- Mixed: combines OpenAI and Anthropic for domain-specific routing.

## 3) Set API Keys

In `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
```

Use only keys required by the selected preset.

## 4) Start Server

### Option A (OpenClaw-specific server)

```bash
set -a; source .env; set +a
python3 -m flowgate.integrations.openclaw.openai_server \
  --host 127.0.0.1 \
  --port 8084 \
  --config examples/configs/anthropic-only.yaml \
  --auth-token local-openclaw-token \
  --stats-auth-token local-stats-token \
  --max-body-bytes 2000000 \
  --socket-timeout 30
```

### Option B (Gateway server)

```bash
set -a; source .env; set +a
flowgate-gateway --port 8084 --mode agent --config examples/configs/anthropic-only.yaml
```

Background mode:

```bash
nohup flowgate-gateway --port 8084 --mode agent --config examples/configs/anthropic-only.yaml > /tmp/cf.log 2>&1 &
```

## 5) Configure OpenClaw Custom Provider

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "flowgate": {
        "baseUrl": "http://<flowgate-host>:8084/v1",
        "apiKey": "local-openclaw-token",
        "api": "openai-completions",
        "models": [
          {
            "id": "flowgate",
            "name": "FlowGate",
            "reasoning": false,
            "input": ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 200000,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```

Host notes:
- If OpenClaw and FlowGate run on the same machine, keep `127.0.0.1`.
- If FlowGate runs on another machine, use that server IP or domain.

If server runs elsewhere, users should replace it with their host/IP, e.g.:
- `http://<server-ip>:8084/v1` or `https://<domain>/v1` (behind proxy/TLS).
- Keep `apiKey` equal to the server auth token value.

## 6) Create OpenClaw Agent

```json
{
  "id": "flowgate",
  "name": "FlowGate",
  "model": "flowgate/flowgate",
  "workspace": "/path/to/workspace-flowgate"
}
```

## 7) Optional Alias And Commands

Alias config:

```json
{
  "agents": {
    "defaults": {
      "models": {
        "flowgate/flowgate": {
          "alias": "cflow",
          "streaming": false
        }
      }
    }
  }
}
```

User commands:

- `/model cflow`: switch model using alias.
- `/cascade`: optional custom command only if OpenClaw side defines it.
- `/cascade savings`: optional custom subcommand pattern for cost breakdown.
- `/cascade health`: optional custom subcommand pattern for status checks.

## 8) Optional Binding Example

```json
{
  "bindings": [
    {
      "agentId": "flowgate",
      "match": {"channel": "telegram", "accountId": "flowgate"}
    }
  ]
}
```

## Key Concepts Users Must Understand

- FlowGate exposes OpenAI-compatible chat completions.
- OpenClaw treats FlowGate as a standard provider.
- Cascade routing: cheap drafter first, verifier only when needed.
- OpenClaw-native event/domain understanding: metadata-driven channel and domain routing.
- Domain routing: code, reasoning, creative, and others can use different model pairs.
- Savings metrics available at `/stats`.

Stats example:

```bash
curl -s http://<flowgate-host>:8084/stats -H "Authorization: Bearer local-stats-token"
```

## Streaming And Compatibility Notes

- Keep base URL with `/v1` prefix.
- Handle clients that hardcode `stream: true`.
- Ensure SSE sends delta chunks, final stop chunk, optional usage chunk, then `[DONE]`.

## Validation Checklist

- `name` in `SKILL.md` equals `flowgate`.
- Upload folder name equals slug (`flowgate`).
- `/model cflow` guidance is present.
- `/cascade` is documented as optional/custom.
- All three preset files are documented.

Run validator:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py /path/to/flowgate
```
