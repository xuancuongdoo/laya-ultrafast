"""Ultrafast chooses an observed action. Code owns execution."""

from ultrafast.agent import Agent
from ultrafast.browser import Browser
from ultrafast.models import (
    ActionElement,
    ActionSpace,
    ActResult,
    AgentSnapshot,
    AgentState,
    Decision,
    FieldContext,
    FieldTextResult,
    HistoryEntry,
    ObservedAction,
    PageObservation,
    TaskResult,
    VerificationResult,
)

__version__ = "0.1.0"

__all__ = [
    "ActResult",
    "ActionElement",
    "ActionSpace",
    "Agent",
    "AgentSnapshot",
    "AgentState",
    "Browser",
    "Decision",
    "FieldContext",
    "FieldTextResult",
    "HistoryEntry",
    "ObservedAction",
    "PageObservation",
    "TaskResult",
    "VerificationResult",
    "__version__",
]
