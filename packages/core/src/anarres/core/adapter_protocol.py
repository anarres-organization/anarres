"""Runtime protocol shared by the native CLI and domain adapters."""

from __future__ import annotations

ADAPTER_PROTOCOL_VERSION = "2"
PROTOCOL_FLAG = "--anarres-adapter-protocol"
NAME_FLAG = "--anarres-adapter-name"


def consume_adapter_invocation(arguments: list[str], *, expected_name: str) -> list[str]:
    """Validate and remove the native CLI's runtime handshake.

    Direct adapter invocation remains supported. When the native CLI supplies a
    handshake, incompatible protocol versions and adapter identities fail before
    a domain workflow can open study artifacts.
    """

    if not arguments or arguments[0] != PROTOCOL_FLAG:
        return arguments
    if len(arguments) < 4 or arguments[2] != NAME_FLAG:
        raise ValueError("malformed Anarres adapter runtime handshake")
    if arguments[1] != ADAPTER_PROTOCOL_VERSION:
        raise ValueError(
            "unsupported Anarres adapter protocol "
            f"{arguments[1]!r}; expected {ADAPTER_PROTOCOL_VERSION}"
        )
    if arguments[3] != expected_name:
        raise ValueError(f"adapter identity {arguments[3]!r} does not match {expected_name!r}")
    return arguments[4:]
