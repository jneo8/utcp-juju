# utcp-juju

Juju tools for AI agents, as native function tools.

The tools are generated from Juju's own API schema
(`apiserver/facades/schema.json`, the facade RPC equivalent of an OpenAPI document) and
executed over a websocket straight to the controller. The agent host needs no `juju`
binary, no client store and no separate server process.

- **Generated from an allowlist**: each allowlisted facade method becomes one tool, with
  its parameters and result described by Juju's schema. `just list-tools` shows the set.
- **Read-only mode by default**: the manual is built from an allowlist of facade methods
  that only read state, so write methods do not exist for the agent. Pair it with a Juju
  user that has only `read` and the controller enforces it as well.
- **Adapters** for the OpenAI Agents SDK and Google ADK. The tool set is also a
  [UTCP](https://www.utcp.io) manual with a `juju` protocol plugin, for hosts that already
  run a UTCP client.

For why it is built this way, see [About the design](docs/explanation/design.md).

## Install

```bash
pip install 'utcp-juju[openai-agents]'   # or [google-adk]
```

## Configure

| Variable | Meaning |
|---|---|
| `UTCP_JUJU_ENDPOINT` | Controller API address `host:17070`; comma-separated to try several |
| `UTCP_JUJU_CA_CERT` | Controller CA certificate, PEM text (or `UTCP_JUJU_CA_CERT_FILE` for a path) |
| `UTCP_JUJU_USERNAME` | A local Juju user |
| `UTCP_JUJU_PASSWORD` | Its password |

For the default read-only mode, create a dedicated user that can only read:

```bash
juju add-user agent-ro
juju change-user-password agent-ro
juju grant agent-ro read <model>          # once per model the agent may see
juju show-controller --show-password      # api-endpoints and ca-cert
```

## Use

```python
from agents import Agent
from utcp_juju import for_openai_agents

agent = Agent(
    name='juju',
    instructions='Answer questions about Juju models.',
    tools=for_openai_agents(),
)
```

```python
from google.adk.agents import Agent
from utcp_juju import for_google_adk

agent = Agent(name='juju', model=GEMINI_MODEL, tools=for_google_adk())
```

Without a framework:

```python
from utcp_juju import JujuTools

tools = JujuTools()  # config from the environment
print(list(tools.specs))  # tool names in the bundled manual
result = await tools.call(name, {'model': 'prod', **arguments})
```

With a UTCP client, either manual call template works once `utcp-juju` is installed:

```python
{'name': 'juju', 'call_template_type': 'juju'}
{
    'name': 'juju',
    'call_template_type': 'file',
    'file_path': str(utcp_juju.utcp_manual()),
    'allowed_communication_protocols': ['juju'],
}  # required, or every tool is filtered out
```

## Examples

`examples/` has two minimal agents with the Juju tools, one built with Google ADK and one
with the OpenAI Agents SDK, both working with a Gemini or an OpenAI API key, and a plain
UTCP client that calls the tools without an LLM. See
[examples/README.md](examples/README.md) for setup and usage.

## What the plugin does for the agent

- Model names instead of UUIDs: `prod`, `owner/prod` or a UUID.
- Errors from Juju come back as text the agent can read.

## Development

`just` lists the recipes. The ones that matter:

| Recipe | Does |
|---|---|
| `just lint` | ruff check and format check |
| `just unit-test` | unit tests against a fake controller; no Juju needed |
| `just functional-test` | tests against the current Juju controller (LXD), in a temporary model (pytest-jubilant) |
| `just vendor-schema` | copy `schema.json` of a release tag from a juju git checkout |
| `just gen-manual` | regenerate `utcp_juju/data/juju.utcp.json` |
| `just check-manual` | fail if the committed manual is stale |
| `just list-tools` | print the tools in the manual |

### Add a tool

1. Find the facade method in `schemas/<series>/schema.json`.
2. Read its apiserver implementation in juju at the commit recorded in
   `schemas/<series>/source.yaml`, and confirm it only reads state.
3. Add the method under its facade in `manualgen/allowlist.yaml`, with a one-sentence
   `description` for the agent.
4. Run `just gen-manual`, then `just unit-test`.

### Update the vendored schema

1. Run `just vendor-schema tag=<tag>`; it rewrites `schema.json` and the commit in
   `source.yaml`.
2. Review the git diff of `schema.json` for changes to allowlisted methods.
3. Run `just gen-manual`, then `just unit-test`.
