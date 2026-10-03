"""A minimal agent that answers questions about a Juju model.

Built with the OpenAI Agents SDK; the LLM is reached through LiteLLM, so either a Gemini or
an OpenAI API key works. Its Juju tools run in their default read-only mode, so it can look but not
touch. Needs the UTCP_JUJU_* variables (see README) and GEMINI_API_KEY or OPENAI_API_KEY.

    uv run --group examples python examples/juju_agent.py utcp-example 'Is anything broken?'
"""

import argparse
import asyncio
import os

from agents import Agent, Runner, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel

from utcp_juju import for_openai_agents

# LiteLLM model per API key, in order of preference when several keys are exported.
DEFAULT_MODELS = {
    'GEMINI_API_KEY': 'gemini/gemini-3.8-flash',
    'OPENAI_API_KEY': 'openai/gpt-5-mini',
}

INSTRUCTIONS = """\
You answer questions about the Juju model `{model}` for an operator.
Use the Juju tools, always with model `{model}`; when the question is about a few
applications, units or machines, use the tools' filter arguments to narrow the result.
Base every statement on tool results, name the units or machines you mean, and say so
when the result does not answer the question. You cannot change anything in Juju.
"""


def default_model() -> str:
    """The LiteLLM model for the first API key found in the environment."""
    for key, model in DEFAULT_MODELS.items():
        if os.environ.get(key):
            return model
    raise SystemExit(f'export one of {", ".join(DEFAULT_MODELS)}, or set LLM_MODEL')


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('model', help='Juju model name, owner/name, or UUID')
    parser.add_argument('prompt', help='question to ask the agent')
    parser.add_argument(
        '--llm',
        default=os.environ.get('LLM_MODEL'),
        help='LiteLLM model, e.g. gemini/gemini-2.5-pro or openai/gpt-5 '
        '(default: LLM_MODEL, else picked from the exported API key)',
    )
    args = parser.parse_args()

    # Tracing uploads to OpenAI and needs an OpenAI key; it is not needed for the example.
    set_tracing_disabled(True)
    agent = Agent(
        name='juju',
        instructions=INSTRUCTIONS.format(model=args.model),
        model=LitellmModel(model=args.llm or default_model()),
        tools=for_openai_agents(),
    )
    result = await Runner.run(agent, args.prompt)
    print(result.final_output)


if __name__ == '__main__':
    asyncio.run(main())
