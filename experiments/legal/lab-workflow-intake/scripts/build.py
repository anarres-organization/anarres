#!/usr/bin/env python3
"""Compatibility import for the packaged outcome-blind LAB intake."""

from anarres.legal.lab_intake import LabIntakeError, build, inspect_task, write

__all__ = ["LabIntakeError", "build", "inspect_task", "write"]
