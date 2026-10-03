"""The ``juju`` call template."""

from typing import Any, Literal

from pydantic import Field
from utcp.data.call_template import CallTemplate
from utcp.interfaces.serializer import Serializer

CALL_TEMPLATE_TYPE = 'juju'


class JujuCallTemplate(CallTemplate):
    """How to execute one Juju facade method on a model.

    As a manual call template (no ``facade``) it stands for the manual bundled with this
    package; as a tool call template it names the facade method to request.

    Attributes:
        facade: Facade name, e.g. ``Client``.
        method: Method name, e.g. ``FullStatus``.
        versions: Juju series (``3.6``) to the facade version to request.
        default_params: Arguments used when the caller omits them.
    """

    call_template_type: Literal['juju'] = CALL_TEMPLATE_TYPE
    facade: str | None = None
    method: str | None = None
    versions: dict[str, int] = Field(default_factory=dict)
    default_params: dict[str, Any] = Field(default_factory=dict)


class JujuCallTemplateSerializer(Serializer[JujuCallTemplate]):
    """Serializer registered for the ``juju`` call template type."""

    def to_dict(self, obj: JujuCallTemplate) -> dict:
        """Convert the call template to a dictionary."""
        dumped = obj.model_dump(exclude_defaults=True, exclude_none=True)
        return dumped | {'call_template_type': CALL_TEMPLATE_TYPE}

    def validate_dict(self, obj: dict) -> JujuCallTemplate:
        """Validate a dictionary into a call template."""
        return JujuCallTemplate.model_validate(obj)
