from pathlib import Path

import pytest
from pydantic import ValidationError

from manualgen.allowlist import Allowlist
from manualgen.facade_schema import SchemaError, parse_facades
from manualgen.generator import GenerationError, generate, render, snake, truncate
from utcp_juju import load_manual, utcp_manual

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_FILE = ROOT / 'manualgen' / 'allowlist.yaml'
SCHEMA_FILE = ROOT / 'schemas' / '3.6' / 'schema.json'

SCHEMA = """[{
  "Name": "Client", "Version": 8,
  "Schema": {
    "properties": {"FullStatus": {"properties": {
      "Params": {"$ref": "#/definitions/StatusParams"},
      "Result": {"$ref": "#/definitions/Status"}}}},
    "definitions": {
      "StatusParams": {"type": "object",
        "properties": {"patterns": {"type": "array", "items": {"type": "string"}}},
        "required": ["patterns"]},
      "Status": {"type": "object", "properties": {"parent": {"$ref": "#/definitions/Status"}}}}
  }
}]"""


def allowlist(**options):
    method = {'description': 'd', **options}
    return Allowlist.model_validate(
        {'series': '3.6', 'facades': {'Client': {'methods': {'FullStatus': method}}}}
    )


def test_committed_manual_is_current():
    expected = render(
        parse_facades(SCHEMA_FILE.read_bytes()), Allowlist.from_yaml(ALLOWLIST_FILE.read_text())
    )
    assert utcp_manual().read_text() == expected


def test_full_status_tool():
    (spec,) = load_manual()
    assert spec.name == 'client.full_status'
    assert 'read-only' in spec.tags
    assert spec.inputs['required'] == ['model']
    assert set(spec.inputs['properties']) == {'model', 'patterns', 'include-storage'}
    assert set(spec.outputs['properties']) >= {'applications', 'machines', 'model', 'relations'}
    assert spec.template.facade == 'Client'
    assert spec.template.method == 'FullStatus'
    assert spec.template.versions == {'3.6': 8}
    assert spec.template.default_params == {'patterns': []}
    assert '$ref' not in utcp_manual().read_text()


def test_generate_resolves_refs_and_drops_defaulted_arguments_from_required():
    manual = generate(parse_facades(SCHEMA), allowlist(default_params={'patterns': []}))
    (tool,) = manual['tools']
    assert tool['inputs']['properties']['patterns'] == {
        'type': 'array',
        'items': {'type': 'string'},
    }
    assert tool['inputs']['required'] == ['model']
    # A type that contains itself is cut off instead of recursing forever.
    assert tool['outputs']['properties']['parent'] == {'type': 'object'}
    assert tool['tool_call_template'] == {
        'call_template_type': 'juju',
        'name': 'juju',
        'facade': 'Client',
        'method': 'FullStatus',
        'versions': {'3.6': 8},
        'default_params': {'patterns': []},
    }


def test_required_arguments_without_defaults_stay_required():
    (tool,) = generate(parse_facades(SCHEMA), allowlist())['tools']
    assert tool['inputs']['required'] == ['model', 'patterns']


def test_schema_and_allowlist_mismatches_are_rejected():
    facades = parse_facades(SCHEMA)
    with pytest.raises(GenerationError, match='default_params names unknown'):
        generate(facades, allowlist(default_params={'nope': 1}))
    with pytest.raises(GenerationError, match='facade Client is not in the schema'):
        generate({}, allowlist())
    missing = Allowlist.model_validate(
        {
            'series': '3.6',
            'facades': {'Client': {'methods': {'Nope': {'description': 'd'}}}},
        }
    )
    with pytest.raises(GenerationError, match=r'Client\.Nope is not in the schema'):
        generate(facades, missing)


def test_unknown_definition_is_an_error():
    broken = SCHEMA.replace('#/definitions/StatusParams', '#/definitions/Missing')
    with pytest.raises(SchemaError, match='unknown definition #/definitions/Missing'):
        generate(parse_facades(broken), allowlist())


@pytest.mark.parametrize(
    'options',
    [
        {'description': ''},
        {'defualt_params': {}},
    ],
)
def test_invalid_allowlist_entries_are_rejected(options):
    with pytest.raises(ValidationError):
        allowlist(**options)


@pytest.mark.parametrize(
    ('name', 'expected'),
    [
        ('FullStatus', 'full_status'),
        ('SubnetsByCIDR', 'subnets_by_cidr'),
        ('SLALevel', 'sla_level'),
        ('SSHClient', 'ssh_client'),
    ],
)
def test_snake(name, expected):
    assert snake(name) == expected


def test_truncate_keeps_annotations_down_to_the_cut():
    schema = {
        'type': 'object',
        'description': 'top',
        'properties': {
            'a': {
                'type': 'array',
                'items': {'type': 'object', 'properties': {'b': {'type': 'string'}}},
            }
        },
    }
    assert truncate(schema, 2) == {
        'type': 'object',
        'description': 'top',
        'properties': {'a': {'type': 'array', 'items': {'type': 'object'}}},
    }
