# Example: a Juju agent

`juju_agent.py` is a minimal [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
agent that answers questions about one Juju model with the Juju tools in their default read-only mode, so
it can look but cannot change anything. It reaches the LLM through
[LiteLLM](https://docs.litellm.ai), so a Gemini API key or an OpenAI API key works.

Every step below is a `just` recipe in this directory; `just` alone lists them.

## Prerequisites

- A Juju controller you are logged in to with the `juju` CLI (only the setup steps use
  it; the agent itself talks to the controller API directly).
- A Gemini API key or an OpenAI API key.
- [`uv`](https://docs.astral.sh/uv/) and [`just`](https://just.systems).

## 1. Deploy the example model

```bash
just deploy-model
```

creates the model `utcp-example` on the current controller, deploys two units of the
`ubuntu` charm, waits until they are active (up to 20 minutes) and prints `juju status`.
Remove it all afterwards with `just destroy-model`.

Every recipe uses `utcp-example` unless told otherwise. To point the example at a model you
already have, skip this step and pass the name to each recipe: `just model=prod run`.

## 2. Create a read-only Juju user

```bash
just create-reader                  # user agent-ro, read on utcp-example
just create-reader my-reader        # or pick the user name
```

This runs `juju add-user`, asks you for the new user's password, and grants it `read` on the
model. Re-running `add-user` for an existing user fails; to let it see another model, use
`juju grant agent-ro read <model>`.

The agent never gets more than this user can do: even a write the tool does not offer would be
refused by the controller.

## 3. Export the settings

```bash
just env
```

prints the lines to run, with the controller endpoint and CA certificate filled in from the
current controller (the certificate is saved to `examples/.juju-ca.pem`):

```bash
export UTCP_JUJU_ENDPOINT=10.0.0.1:17070
export UTCP_JUJU_CA_CERT_FILE='/path/to/examples/.juju-ca.pem'
export UTCP_JUJU_USERNAME='agent-ro'
export UTCP_JUJU_PASSWORD=...        # the password set in create-reader
export GEMINI_API_KEY=...            # your Gemini API key, or:
# export OPENAI_API_KEY=sk-...       # your OpenAI API key
```

Fill in the password and one of the API keys, run the lines in your shell, then check:

```bash
just check-env
```

The LLM follows the key: a Gemini model with `GEMINI_API_KEY`, else an OpenAI model with
`OPENAI_API_KEY` (Gemini wins if both are set); the defaults are in `juju_agent.py`. To
pick another, set a [LiteLLM model name](https://docs.litellm.ai/docs/providers):

```bash
export LLM_MODEL=gemini/<model>
```

## 4. Ask a question

```bash
just run                                         # default: which units are not active/idle, and why
just run 'Which machines are the ubuntu units on, and what are their addresses?'
just model=prod run 'Summarise the relations of the postgresql application.'
```

From the repository root the same run is `just example '...'`.

## 5. Clean up

```bash
just destroy-model                  # removes utcp-example and its machines
juju remove-user agent-ro --yes     # if you no longer need the user
```

## What happens

1. `for_openai_agents()` turns the bundled UTCP manual into one `FunctionTool`; the agent's
   model is a `LitellmModel`, so the tool works the same with Gemini or OpenAI.
2. The agent picks a tool and calls it with `{"model": "utcp-example", ...}`.
3. The tool logs in to the controller over its websocket API as the read-only user, looks up
   the model's UUID, sends the facade request, and returns the JSON.
4. The agent answers from that JSON.

## Troubleshooting

| Message | Cause |
|---|---|
| `export these first: ...` | a variable from step 3 is not exported in this shell |
| `invalid entity name or password` | wrong `UTCP_JUJU_USERNAME` / `UTCP_JUJU_PASSWORD` |
| `cannot connect to the Juju controller` | wrong endpoint, or the CA file is not this controller's |
| `model 'x' not found; models visible to this user: ...` | the user has no `read` grant on that model |
| `... is not available for Juju <version>` | the manual has no facade version for that Juju series |
