"""Laya chooses an observed action. Code owns execution."""

from .laya_agent import LayaAgent as Agent
from .laya_browser import Browser

__all__ = ["Agent", "Browser"]
