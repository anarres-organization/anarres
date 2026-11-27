"""Source-driver interface and discovery."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import entry_points
from typing import Any, Protocol

from anarres.core import EnvironmentSource

from ..contract import RoboticsContractError, SourceDescription

ENTRY_POINT_GROUP = "anarres.robotics.source_drivers"
BUILTIN_DRIVERS = {"robotics-fixture-v1": "anarres.robotics.drivers.fixture:FixtureDriver"}


class SourceDriver(Protocol):
    """Translate one native robotics format into the portable input contract."""

    native_format: str
    version: str

    def describe(self, source: EnvironmentSource) -> SourceDescription:
        """Validate the native source and report its scientific meaning."""

    def tasks(self, source: EnvironmentSource) -> list[dict[str, Any]]:
        """Return the ordered probe tasks with their initial-state identities and seeds."""


def _registered() -> dict[str, str]:
    registered = dict(BUILTIN_DRIVERS)
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        if entry.name in registered and registered[entry.name] != entry.value:
            raise RoboticsContractError(f"two drivers claim native format {entry.name}")
        registered[entry.name] = entry.value
    return registered


def installed_formats() -> list[str]:
    """List accepted native formats without importing any driver."""

    return sorted(_registered())


def load_driver(native_format: str) -> SourceDriver:
    target = _registered().get(native_format)
    if target is None:
        raise RoboticsContractError(f"no installed driver for native format {native_format}")
    module_name, _, attribute = target.partition(":")
    driver = getattr(import_module(module_name), attribute)()
    if driver.native_format != native_format:
        raise RoboticsContractError(
            f"driver registered as {native_format} declares {driver.native_format}"
        )
    return driver
