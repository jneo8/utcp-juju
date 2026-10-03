"""Call the Juju tools through a plain UTCP client, the way a UTCP host does. No LLM.

Installing utcp-juju registers its `juju` plugin with UTCP, so the client only needs one
manual entry of type `juju`; the plugin supplies the bundled manual and executes its tools.
Needs the UTCP_JUJU_* variables (see README).

    just run-utcp-example                              # list the tools
    just run-utcp-example juju.<facade>.<method>       # call one on the example model
"""

import argparse
import asyncio
import json
import logging

from utcp.utcp_client import UtcpClient

from utcp_juju import JujuError

# The whole client-side setup: one manual, handled by the `juju` plugin.
CONFIG = {'manual_call_templates': [{'name': 'juju', 'call_template_type': 'juju'}]}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('tool', nargs='?', help='tool to call; lists the tools when omitted')
    parser.add_argument('arguments', nargs='?', default='{}', help='tool arguments as JSON')
    parser.add_argument('--model', help='Juju model, added to the arguments when they have none')
    args = parser.parse_args()
    # UTCP logs every plugin it registers at INFO.
    logging.getLogger('utcp').setLevel(logging.WARNING)

    client = await UtcpClient.create(config=CONFIG)
    if not args.tool:
        for tool in await client.search_tools('', limit=1000):
            print(f'{tool.name}\n    {tool.description}')
        return

    arguments = json.loads(args.arguments)
    if args.model:
        arguments.setdefault('model', args.model)
    try:
        result = await client.call_tool(args.tool, arguments)
    except JujuError as exc:
        raise SystemExit(f'Juju error: {exc.message}') from None
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
