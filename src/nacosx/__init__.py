"""
NacosX - A decorator-based Python library for automatic Nacos service registration.

This library provides automatic service registration, heartbeat management,
and graceful shutdown with built-in retry and self-healing support.
"""

__version__ = "0.1.dev0"
__author__ = "ProgrammerPlus1998"

from .core import (
    NacosService,
    nacos_registry,
    DEFAULT_REGISTER_RETRIES,
    DEFAULT_REGISTER_RETRY_DELAY,
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_HEARTBEAT_MAX_FAILURES,
    DEFAULT_HEARTBEAT_RETRY_DELAY,
    DEFAULT_UNREGISTER_TIMEOUT,
)

__all__ = [
    "NacosService",
    "nacos_registry",
    "DEFAULT_REGISTER_RETRIES",
    "DEFAULT_REGISTER_RETRY_DELAY",
    "DEFAULT_HEARTBEAT_INTERVAL",
    "DEFAULT_HEARTBEAT_MAX_FAILURES",
    "DEFAULT_HEARTBEAT_RETRY_DELAY",
    "DEFAULT_UNREGISTER_TIMEOUT",
]
