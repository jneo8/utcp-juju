"""A minimal Google ADK agent that answers questions about a Juju model.

The LLM is reached through LiteLLM, so either a Gemini or an OpenAI API key works. Its Juju
tools run in their default read-only mode, so it can look but not touch. Needs the
UTCP_JUJU_* variables (see README) and GEMINI_API_KEY or OPENAI_API_KEY.

    just run-google-example 'Is anything broken?'
"""

import argparse
import asyncio

from common import INSTRUCTIONS, llm_model
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

from utcp_juju import for_google_adk

APP_NAME = 'juju-example'
USER_ID = 'operator'


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('model', help='Juju model name, owner/name, or UUID')
    parser.add_argument('prompt', help='question to ask the agent')
    parser.add_argument('--llm', help='LiteLLM model name (default: LLM_MODEL, else by API key)')
    args = parser.parse_args()

    agent = Agent(
        name='juju',
        model=LiteLlm(model=args.llm or llm_model()),
        instruction=INSTRUCTIONS.format(model=args.model),
        tools=for_google_adk(),
    )
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    message = types.Content(role='user', parts=[types.Part(text=args.prompt)])
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            print(''.join(part.text or '' for part in event.content.parts))


if __name__ == '__main__':
    asyncio.run(main())
