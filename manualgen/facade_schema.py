"""Juju's ``apiserver/facades/schema.json``: one JSON Schema document per facade."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

JsonSchema = dict[str, Any]


class SchemaError(Exception):
    """The facade schema cannot be read as expected."""


class _MethodIO(BaseModel):
    params: JsonSchema | None = Field(None, alias='Params')
    result: JsonSchema | None = Field(None, alias='Result')


class _Method(BaseModel):
    properties: _MethodIO = _MethodIO()


class _FacadeDocument(BaseModel):
    properties: dict[str, _Method] = {}
    definitions: dict[str, JsonSchema] = {}


class Facade(BaseModel):
    """One facade entry of schema.json."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(alias='Name')
    version: int = Field(alias='Version')
    document: _FacadeDocument = Field(alias='Schema')

    def has_method(self, method: str) -> bool:
        """Whether the facade defines ``method``."""
        return method in self.document.properties

    def params(self, method: str) -> JsonSchema:
        """The method's params schema with every ``$ref`` expanded; empty object if none."""
        node = self.document.properties[method].properties.params
        return self.resolve(node) if node else {'type': 'object', 'properties': {}}

    def result(self, method: str) -> JsonSchema:
        """The method's result schema with every ``$ref`` expanded; bare object if none."""
        node = self.document.properties[method].properties.result
        return self.resolve(node) if node else {'type': 'object'}

    def resolve(self, node: Any, _seen: tuple[str, ...] = ()) -> Any:
        """Expand ``$ref`` nodes inline. A type that contains itself becomes a bare object."""
        if isinstance(node, list):
            return [self.resolve(item, _seen) for item in node]
        if not isinstance(node, dict):
            return node
        ref = node.get('$ref')
        if ref is None:
            return {key: self.resolve(value, _seen) for key, value in node.items()}
        name = ref.removeprefix('#/definitions/')
        if name in _seen:
            return {'type': 'object'}
        if name not in self.document.definitions:
            raise SchemaError(f'{self.name}: unknown definition {ref}')
        return self.resolve(self.document.definitions[name], (*_seen, name))


_FACADES = TypeAdapter(list[Facade])


def parse_facades(raw: bytes | str) -> dict[str, Facade]:
    """Parse schema.json into facades by name."""
    return {facade.name: facade for facade in _FACADES.validate_json(raw)}
