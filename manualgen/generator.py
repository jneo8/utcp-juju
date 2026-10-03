"""Build the UTCP manual from the facade schema and the allowlist."""

import json
import re
from typing import Any

from utcp.data.utcp_manual import UtcpManualSerializer

from manualgen.allowlist import Allowlist, MethodEntry
from manualgen.facade_schema import Facade, JsonSchema
from utcp_juju.call_template import JujuCallTemplate, JujuCallTemplateSerializer

# Levels of the result schema kept in `outputs`; FullStatus in full is far too large.
OUTPUT_DEPTH = 2
# Keys whose values are themselves schemas, and so count as one level deeper.
_SUBSCHEMA_KEYS = ('properties', 'patternProperties')
MODEL_INPUT: JsonSchema = {
    'type': 'string',
    'description': 'Model name, `owner/name`, or model UUID.',
}


class GenerationError(Exception):
    """The allowlist and the facade schema disagree."""


def snake(name: str) -> str:
    """``FullStatus`` -> ``full_status``, ``SubnetsByCIDR`` -> ``subnets_by_cidr``."""
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', name).lower()


def truncate(schema: Any, depth: int) -> Any:
    """Keep ``depth`` levels of nested schemas; below that, only each schema's type."""
    if not isinstance(schema, dict):
        return schema
    if depth == 0:
        return {'type': schema.get('type', 'object')}
    out = {}
    for key, value in schema.items():
        if key in _SUBSCHEMA_KEYS:
            out[key] = {name: truncate(sub, depth - 1) for name, sub in value.items()}
        elif key in {'items', 'additionalProperties'} and isinstance(value, dict):
            out[key] = truncate(value, depth - 1)
        else:
            out[key] = value
    return out


def build_tool(facade: Facade, method: str, entry: MethodEntry, series: str) -> dict[str, Any]:
    """The UTCP tool for one allowlisted facade method."""
    params = facade.params(method)
    arguments = params.get('properties', {})
    unknown = sorted(set(entry.default_params) - set(arguments))
    if unknown:
        raise GenerationError(f'{facade.name}.{method}: default_params names unknown {unknown}')

    required = [arg for arg in params.get('required', []) if arg not in entry.default_params]
    template = JujuCallTemplate(
        name='juju',
        facade=facade.name,
        method=method,
        versions={series: facade.version},
        default_params=entry.default_params,
    )
    return {
        'name': f'{snake(facade.name)}.{snake(method)}',
        'description': entry.description,
        'inputs': {
            'type': 'object',
            'properties': {'model': MODEL_INPUT, **arguments},
            'required': ['model', *required],
        },
        'outputs': truncate(facade.result(method), OUTPUT_DEPTH),
        'tags': ['juju', 'read-only', snake(facade.name)],
        'tool_call_template': JujuCallTemplateSerializer().to_dict(template),
    }


def generate(facades: dict[str, Facade], allowlist: Allowlist) -> dict[str, Any]:
    """The manual document, validated as a UTCP manual."""
    tools = []
    for facade_name, facade_entry in allowlist.facades.items():
        facade = facades.get(facade_name)
        if facade is None:
            raise GenerationError(f'facade {facade_name} is not in the schema')
        for method, entry in facade_entry.methods.items():
            if not facade.has_method(method):
                raise GenerationError(f'{facade_name}.{method} is not in the schema')
            tools.append(build_tool(facade, method, entry, allowlist.series))
    tools.sort(key=lambda tool: tool['name'])
    manual = {'manual_version': f'juju-{allowlist.series}', 'tools': tools}
    # Validation fills in utcp_version; the dict itself stays free of null defaults.
    validated = UtcpManualSerializer().validate_dict(manual)
    return {'utcp_version': validated.utcp_version, **manual}


def render(facades: dict[str, Facade], allowlist: Allowlist) -> str:
    """The manual as the exact text written to disk."""
    return json.dumps(generate(facades, allowlist), indent=1) + '\n'
