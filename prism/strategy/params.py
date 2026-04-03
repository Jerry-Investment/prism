"""
PRISM Strategy Parameter Validation Framework

Provides a declarative way to define, document, and validate strategy
parameters.

Usage example::

    class MACrossStrategy(Strategy):
        param_specs = [
            ParamSpec("fast_window", ParamType.INT, default=10, min_val=2, max_val=50,
                      description="Fast MA window"),
            ParamSpec("slow_window", ParamType.INT, default=30, min_val=5, max_val=200,
                      description="Slow MA window"),
        ]

        def _validate_params(self):
            super()._validate_params()
            if self.params["fast_window"] >= self.params["slow_window"]:
                raise ValueError("fast_window must be less than slow_window")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ParamType(str, Enum):
    """Supported parameter types."""

    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STR = "str"
    LIST = "list"


@dataclass
class ParamSpec:
    """
    Declaration for a single strategy parameter.

    Attributes:
        name:        Parameter name (must match a key in Strategy.params).
        type:        Expected Python type.
        default:     Default value (used when param is missing and required=False).
        required:    If True, the param must be present (no fallback to default).
        min_val:     Minimum numeric value (inclusive).  Only for INT/FLOAT.
        max_val:     Maximum numeric value (inclusive).  Only for INT/FLOAT.
        choices:     If set, value must be one of these choices.
        description: Human-readable documentation.
    """

    name: str
    type: ParamType
    default: Any = None
    required: bool = False
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    choices: Optional[List[Any]] = None
    description: str = ""

    def validate(self, params: Dict[str, Any]) -> None:
        """
        Validate and coerce a single parameter inside *params* in-place.

        Raises:
            ValueError: If the parameter fails a constraint.
            TypeError:  If the parameter cannot be cast to the declared type.
        """
        if self.name not in params:
            if self.required:
                raise ValueError(
                    f"Required parameter '{self.name}' is missing."
                )
            # Apply default
            params[self.name] = self.default
            return

        value = params[self.name]

        # Type coercion / check
        try:
            if self.type == ParamType.INT:
                value = int(value)
            elif self.type == ParamType.FLOAT:
                value = float(value)
            elif self.type == ParamType.BOOL:
                if not isinstance(value, bool):
                    raise TypeError(f"Parameter '{self.name}' must be a bool.")
            elif self.type == ParamType.STR:
                value = str(value)
            elif self.type == ParamType.LIST:
                if not isinstance(value, list):
                    raise TypeError(f"Parameter '{self.name}' must be a list.")
        except (ValueError, TypeError) as exc:
            raise TypeError(
                f"Parameter '{self.name}' could not be cast to {self.type.value}: {exc}"
            ) from exc

        # Range checks
        if self.min_val is not None and value < self.min_val:
            raise ValueError(
                f"Parameter '{self.name}' = {value} is below minimum {self.min_val}."
            )
        if self.max_val is not None and value > self.max_val:
            raise ValueError(
                f"Parameter '{self.name}' = {value} exceeds maximum {self.max_val}."
            )

        # Choices check
        if self.choices is not None and value not in self.choices:
            raise ValueError(
                f"Parameter '{self.name}' = {value!r} is not one of {self.choices}."
            )

        params[self.name] = value


@dataclass
class StrategyParams:
    """
    Convenience wrapper that validates a set of ParamSpecs against a dict.

    Usage::

        specs = [
            ParamSpec("window", ParamType.INT, default=20, min_val=5, required=True),
        ]
        validated = StrategyParams.build({"window": 20}, specs)
    """

    values: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        raw: Dict[str, Any],
        specs: List[ParamSpec],
    ) -> "StrategyParams":
        """Validate *raw* against *specs* and return a StrategyParams."""
        params = dict(raw)
        for spec in specs:
            spec.validate(params)
        return cls(values=params)

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def __repr__(self) -> str:
        return f"StrategyParams({self.values})"
