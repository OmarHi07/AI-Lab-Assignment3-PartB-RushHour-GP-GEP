"""Shared safe expression representation for GP and GEP."""

import math
from dataclasses import dataclass, field
from functools import lru_cache

from features import TERMINAL_NAMES, extract_features


FUNCTION_ARITY = {
    "+": 2,
    "-": 2,
    "*": 2,
    "/": 2,
    "min": 2,
    "max": 2,
    "abs": 1,
}

FUNCTION_NAMES = tuple(FUNCTION_ARITY)
CONSTANTS = (0.0, 0.5, 1.0, 2.0, 3.0, 5.0)
VALUE_LIMIT = 1_000_000.0


def _bounded(value):
    if not math.isfinite(value):
        return 0.0
    return max(-VALUE_LIMIT, min(VALUE_LIMIT, float(value)))


def apply_function(symbol, arguments):
    """Apply a closure-safe numeric function and bound its result."""
    if symbol == "+":
        value = arguments[0] + arguments[1]
    elif symbol == "-":
        value = arguments[0] - arguments[1]
    elif symbol == "*":
        value = arguments[0] * arguments[1]
    elif symbol == "/":
        value = 0.0 if abs(arguments[1]) < 1e-12 else arguments[0] / arguments[1]
    elif symbol == "min":
        value = min(arguments)
    elif symbol == "max":
        value = max(arguments)
    elif symbol == "abs":
        value = abs(arguments[0])
    else:
        raise ValueError(f"Unknown function: {symbol}")
    return _bounded(value)


def constant_symbol(value):
    return f"#{float(value):g}"


def is_constant(symbol):
    return isinstance(symbol, str) and symbol.startswith("#")


@dataclass
class ExpressionNode:
    symbol: str
    children: list = field(default_factory=list)

    def clone(self):
        return ExpressionNode(self.symbol, [child.clone() for child in self.children])

    def evaluate(self, features):
        if self.symbol in TERMINAL_NAMES:
            return features[self.symbol]
        if is_constant(self.symbol):
            return float(self.symbol[1:])
        arguments = [child.evaluate(features) for child in self.children]
        return apply_function(self.symbol, arguments)

    def prefix(self):
        if not self.children:
            return self.symbol
        return f"({self.symbol} {' '.join(child.prefix() for child in self.children)})"

    def infix(self):
        if not self.children:
            return self.symbol[1:] if is_constant(self.symbol) else self.symbol
        if self.symbol == "abs":
            return f"abs({self.children[0].infix()})"
        if self.symbol in {"min", "max"}:
            return f"{self.symbol}({self.children[0].infix()}, {self.children[1].infix()})"
        return f"({self.children[0].infix()} {self.symbol} {self.children[1].infix()})"

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children)

    def operator_count(self):
        return (1 if self.symbol in FUNCTION_ARITY else 0) + sum(
            child.operator_count() for child in self.children
        )

    def depth(self):
        return 1 if not self.children else 1 + max(child.depth() for child in self.children)

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["symbol"],
            [cls.from_dict(child) for child in data.get("children", [])],
        )


def make_heuristic(expression):
    """Wrap an expression tree in the ``h(state)`` interface used by A*."""

    @lru_cache(maxsize=100_000)
    def heuristic(state):
        features = extract_features(state)
        if features["D"] == 0.0:
            return 0.0
        return max(0.0, _bounded(expression.evaluate(features)))

    heuristic.expression = expression
    heuristic.__name__ = "evolved_heuristic"
    return heuristic


def expression_summary(expression):
    return {
        "prefix": expression.prefix(),
        "infix": expression.infix(),
        "node_count": expression.node_count(),
        "operator_count": expression.operator_count(),
        "depth": expression.depth(),
        "tree": expression.to_dict(),
    }
