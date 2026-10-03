"""Errors raised by the Juju RPC plugin."""


class JujuError(Exception):
    """A Juju API error, or a request this plugin refuses to send.

    ``code`` carries Juju's error code when the controller produced the error.
    """

    def __init__(self, message: str, code: str = '') -> None:
        super().__init__(message)
        self.message = message
        self.code = code
