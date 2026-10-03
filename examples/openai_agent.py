"""A minimal OpenAI Agents SDK agent that answers questions about a Juju model.

The LLM is reached through LiteLLM, so either a Gemini or an OpenAI API key works. Its Juju
tools run in their default read-only mode, so it can look but not touch. Needs the
UTCP_JUJU_* variables (see README) and GEMINI_API_KEY or OPENAI_API_KEY.

    just run-openai-example 'Is anything broken?'
"""

import argparse
import asyncio

from agents import Agent, Runner, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel
from common import INSTRUCTIONS, llm_model

from utcp_juju import for_openai_agents


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('model', help='Juju model name, owner/name, or UUID')
    parser.add_argument('prompt', help='question to ask the agent')
    parser.add_argument('--llm', help='LiteLLM model name (default: LLM_MODEL, else by API key)')
    args = parser.parse_args()

    # Tracing uploads to OpenAI and needs an OpenAI key; it is not needed for the example.
    set_tracing_disabled(True)
    agent = Agent(
        name='juju',
        instructions=INSTRUCTIONS.format(model=args.model),
        model=LitellmModel(model=args.llm or llm_model()),
        tools=for_openai_agents(),
    )
    result = await Runner.run(agent, args.prompt)
    print(result.final_output)


if __name__ == '__main__':
    asyncio.run(main())
