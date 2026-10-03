import json

from utcp_juju import JujuTools, for_google_adk, for_openai_agents


def test_tools_are_named_as_functions():
    (tool,) = JujuTools().tools()
    assert tool.name == 'juju_client_full_status'
    assert tool.parameters['required'] == ['model']


async def test_openai_agents_adapter(controller, config):
    from agents import FunctionTool

    controller.respond('Client.FullStatus', {'model': {'name': 'prod'}})
    (tool,) = for_openai_agents(config)
    assert isinstance(tool, FunctionTool)
    assert tool.name == 'juju_client_full_status'
    assert not tool.strict_json_schema
    result = await tool.on_invoke_tool(None, '{"model": "prod"}')
    assert json.loads(result) == {'model': {'name': 'prod'}}
    assert (await tool.on_invoke_tool(None, '{not json')).startswith('Error: arguments')


async def test_google_adk_adapter(controller, config):
    from google.adk.tools import BaseTool

    controller.respond('Client.FullStatus', {'model': {'name': 'prod'}})
    (tool,) = for_google_adk(config)
    assert isinstance(tool, BaseTool)
    declaration = tool._get_declaration()
    assert declaration.name == 'juju_client_full_status'
    assert declaration.parameters_json_schema['required'] == ['model']
    result = await tool.run_async(args={'model': 'prod'}, tool_context=None)
    assert json.loads(result) == {'model': {'name': 'prod'}}
