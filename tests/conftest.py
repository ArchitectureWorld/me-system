"""Compatibility loader for tests written before the me_system package rename."""

import sys

import me_system

sys.modules.setdefault("me_core", me_system)
