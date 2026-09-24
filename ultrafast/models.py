"""Shared typed boundaries for ultrafast: observations, decisions, history.

Internal code passes these dataclasses around. Only HTTP/JSON edges
(demo server, JSON dumps, CDP payloads) serialize via ``to_dict``.
Every model accepts plain dicts in ``from_dict`` and supports read-only
dict-style access (``obj[\"key\"]``, ``obj.get(k)``, ``k in obj``) so
existing dict-shaped callers keep working during migration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from dataclasses import field as dc_field
from typing import Any, Iterator


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _item(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj[key]
    try:
        return getattr(obj, key)
    except AttributeError:
        raise KeyError(key) from None


class _DictRead:
    def __getitem__(self, key: str) -> Any:
        try:
            return _item(self, key)
        except KeyError:
            raise KeyError(key) from None

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        fields = getattr(type(self), "__dataclass_fields__", None)
        if fields is not None:
            return key in fields and getattr(self, key, None) is not None
        try:
            _item(self, key)
            return True
        except KeyError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return _get(self, key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)


@dataclass
class ObservedAction(_DictRead):
    id: str = ""
    kind: str = ""
    label: str = ""
    node: Any = None
    value: str = ""
    role: str | None = None
    checked: str | None = None
    selected: str | None = None
    expanded: str | None = None
    current_value: str | None = None
    delta: int | None = None
    rect: dict | None = None

    @classmethod
    def from_dict(cls, d: Any) -> ObservedAction:
        if isinstance(d, ObservedAction):
            return d
        d = dict(d or {})
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PageObservation(_DictRead):
    url: str = ""
    title: str = ""
    text: str = ""
    actions: list = dc_field(default_factory=list)
    fingerprint: str = ""
    screenshot: str | None = None
    scroll: dict | None = None
    marker: Any = None
    page_key: Any = None
    guards: dict | None = None
    omitted_actions: int = 0
    w: int | None = None
    h: int | None = None

    @classmethod
    def from_dict(cls, d: Any) -> PageObservation:
        if isinstance(d, PageObservation):
            return d
        d = dict(d or {})
        actions = [ObservedAction.from_dict(a) for a in d.get("actions", [])]
        known = {f for f in cls.__dataclass_fields__}
        kw = {k: v for k, v in d.items() if k in known and k != "actions"}
        return cls(actions=actions, **kw)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["actions"] = [a.to_dict() if isinstance(a, ObservedAction) else dict(a) for a in self.actions]
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ActResult(_DictRead):
    executed: str = ""

    @classmethod
    def from_dict(cls, d: Any) -> ActResult:
        if isinstance(d, ActResult):
            return d
        return cls(executed=dict(d or {}).get("executed", ""))

    def to_dict(self) -> dict:
        return {"executed": self.executed}


@dataclass
class Decision(_DictRead):
    choice: str = ""
    operation: str = ""
    target: str | None = None
    confidence: float = 1.0
    probabilities: dict = dc_field(default_factory=dict)
    latency_ms: int = 0
    usage: dict = dc_field(default_factory=dict)
    operation_probabilities: dict | None = None
    target_probabilities: dict | None = None
    target_confidence: float | None = None
    raw_answers: Any = None
    model: str | None = None
    request: Any = None
    debug: dict | None = None
    fingerprint: str | None = None
    elapsed_ms: int | None = None

    @classmethod
    def from_dict(cls, d: Any) -> Decision:
        if isinstance(d, Decision):
            return d
        d = dict(d or {})
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class HistoryEntry(_DictRead):
    step: int = 0
    action: str = ""
    kind: str = ""
    choice: str = ""
    probability: float = 0.0
    confidence: float = 0.0
    latency_ms: int = 0
    text: str | None = None
    text_helper: str | None = None
    text_latency_ms: int = 0
    operation: str | None = None
    target: str | None = None
    page_changed: bool | None = None
    url: str = ""
    usage: dict | None = None
    executed_ms: int | None = None
    elapsed_ms: int | None = None

    @classmethod
    def from_dict(cls, d: Any) -> HistoryEntry:
        if isinstance(d, HistoryEntry):
            return d
        d = dict(d or {})
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class FieldContext(_DictRead):
    goal: str = ""
    field: dict = dc_field(default_factory=dict)
    page: dict = dc_field(default_factory=dict)
    recent_actions: list = dc_field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Any) -> FieldContext:
        if isinstance(d, FieldContext):
            return d
        d = dict(d or {})
        return cls(
            goal=d.get("goal", ""),
            field=dict(d.get("field", {})),
            page=dict(d.get("page", {})),
            recent_actions=list(d.get("recent_actions", [])),
        )

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "field": dict(self.field),
            "page": dict(self.page),
            "recent_actions": list(self.recent_actions),
        }


@dataclass
class FieldTextResult(_DictRead):
    value: str = ""
    model: str = ""
    latency_ms: int = 0
    usage: dict = dc_field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Any) -> FieldTextResult:
        if isinstance(d, FieldTextResult):
            return d
        d = dict(d or {})
        return cls(
            value=d.get("value", d.get("text", "")),
            model=d.get("model", ""),
            latency_ms=d.get("latency_ms", 0),
            usage=dict(d.get("usage", {})),
        )

    def to_dict(self) -> dict:
        return {"value": self.value, "model": self.model, "latency_ms": self.latency_ms, "usage": dict(self.usage)}


@dataclass
class ActionOption:
    index: str = ""
    label: str = ""
    value: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActionElement(_DictRead):
    index: str = ""
    label: str = ""
    operations: list = dc_field(default_factory=list)
    role: str | None = None
    value: str | None = None
    checked: str | None = None
    selected: str | None = None
    expanded: str | None = None
    options: list = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["options"] = [o.to_dict() if isinstance(o, ActionOption) else dict(o) for o in self.options]
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ActionSpace(_DictRead):
    elements: list = dc_field(default_factory=list)
    targets: dict = dc_field(default_factory=dict)
    controls: dict = dc_field(default_factory=dict)

    def __iter__(self) -> Iterator[Any]:
        yield self.elements
        yield self.targets
        yield self.controls

    def __getitem__(self, key: Any) -> Any:
        if key == 0:
            return self.elements
        if key == 1:
            return self.targets
        if key == 2:
            return self.controls
        return _item(self, key)

    def __len__(self) -> int:
        return 3


@dataclass
class AgentState(_DictRead):
    goal: str = ""
    page: Any = None
    history: list = dc_field(default_factory=list)
    status: str = "ready"
    plan: list = dc_field(default_factory=list)
    plan_index: int = 0
    decisions: list = dc_field(default_factory=list)
    text_calls: list = dc_field(default_factory=list)
    elapsed_ms: int = 0
    started_at: float | None = None
    record: bool = False
    decision: Any = None
    browser: Any = None


@dataclass
class AgentSnapshot(_DictRead):
    status: str = "idle"
    goal: str = ""
    page: Any = None
    decision: Any = None
    history: list = dc_field(default_factory=list)
    plan: list = dc_field(default_factory=list)
    plan_index: int = 0
    decisions: list = dc_field(default_factory=list)
    text_calls: list = dc_field(default_factory=list)
    elapsed_ms: int = 0
    started_at: float | None = None
    record: bool = False
    elements: list = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        def conv(v: Any) -> Any:
            if hasattr(v, "to_dict"):
                return v.to_dict()
            if isinstance(v, list):
                return [conv(i) for i in v]
            if isinstance(v, dict):
                return {k: conv(i) for k, i in v.items()}
            return v

        return {k: conv(v) for k, v in asdict(self).items() if v is not None}


@dataclass
class TaskResult(_DictRead):
    task: str = ""
    success: bool = False
    steps: int = 0
    decisions: int = 0
    backend_latency_ms: int = 0
    wall_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VerificationResult(_DictRead):
    url: str = ""
    title: str = ""
    steps: int = 0
    decisions: int = 0
    latency_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


__all__ = [
    "ActResult",
    "ActionElement",
    "ActionOption",
    "ActionSpace",
    "AgentSnapshot",
    "AgentState",
    "Decision",
    "FieldContext",
    "FieldTextResult",
    "HistoryEntry",
    "ObservedAction",
    "PageObservation",
    "TaskResult",
    "VerificationResult",
]
