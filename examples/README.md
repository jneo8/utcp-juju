# Example: Juju agents

Two minimal agents that answer questions about one Juju model with the Juju tools in their
default read-only mode, so they can look but cannot change anything:

| Agent | Framework | Run with |
|---|---|---|
| `adk_agent.py` | [Google ADK](https://google.github.io/adk-docs/) | `just run-google-example` |
| `openai_agent.py` | [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) | `just run-openai-example` |

Both take a Gemini or an OpenAI API key, and share their instructions and model choice
(`common.py`); they differ only in how the framework is wired.

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

Both agents pick the LLM the same way: a Gemini model with `GEMINI_API_KEY`, else an
OpenAI model with `OPENAI_API_KEY` (Gemini wins if both are set); the defaults are in
`common.py`. To pick another, set a [LiteLLM model name](https://docs.litellm.ai/docs/providers):

```bash
export LLM_MODEL=openai/<model>      # or gemini/<model>
```

Both reach every model through [LiteLLM](https://docs.litellm.ai).

## 4. Ask a question

```bash
just run-google-example              # default question: what is not healthy
just run-google-example 'Which machines are the ubuntu units on, and what are their addresses?'
just run-openai-example 'Which machines are the ubuntu units on?'
just model=prod run-google-example 'Summarise the relations of the postgresql application.'
```

The same recipes exist at the repository root.

## 5. Clean up

```bash
just destroy-model                  # removes utcp-example and its machines
juju remove-user agent-ro --yes     # if you no longer need the user
```

## What happens

1. `for_google_adk()` or `for_openai_agents()` turns the bundled UTCP manual into one
   framework tool per Juju operation.
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
