"""EML AST: parse, evaluate, measure.

Canonical operator (pinned to skills/_shared/eml-foundations.md):
    eml(a, b) = cmath.exp(a) - cmath.log(b)
Leaf alphabet: {"1", "x", "y"}. RPN uses single-char tokens; "E" is the operator.
"""

from __future__ import annotations

import cmath
import json
import re
from dataclasses import dataclass
from typing import Union

LEAF_ALPHABET = frozenset({"1", "x", "y"})


class ParseError(ValueError):
    """Raised when a tree string can't be parsed as an EML tree."""


@dataclass(frozen=True)
class Leaf:
    symbol: str  # "1", "x", or "y"

    def __post_init__(self):
        if self.symbol not in LEAF_ALPHABET:
            raise ParseError(
                f"leaf {self.symbol!r} not in allowed alphabet {sorted(LEAF_ALPHABET)}"
            )


@dataclass(frozen=True)
class EmlNode:
    a: "Node"
    b: "Node"


Node = Union[Leaf, EmlNode]


# ---------- parsing ----------

_NESTED_RE = re.compile(r"\beml\s*\(")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[(),]|E")


def parse(s: str) -> Node:
    """Parse a tree from one of three formats:
    - nested: 'eml(x, 1)' or 'eml(eml(1,1), 1)'
    - RPN:    'x 1 E' or 'x1E' (whitespace optional between single-char tokens)
    - JSON:   '{"eml":[{"leaf":"x"},{"leaf":"1"}]}' or '{"leaf":"x"}'
    """
    s = s.strip()
    if not s:
        raise ParseError("empty input")
    if s.startswith("{"):
        return _parse_json(json.loads(s))
    if _NESTED_RE.search(s):
        node, pos = _parse_nested(s, 0)
        tail = s[pos:].strip()
        if tail:
            raise ParseError(f"unexpected trailing text: {tail!r}")
        return node
    return _parse_rpn(s)


def _parse_json(obj) -> Node:
    if isinstance(obj, dict) and "leaf" in obj:
        return Leaf(str(obj["leaf"]))
    if isinstance(obj, dict) and "eml" in obj:
        a, b = obj["eml"]
        return EmlNode(_parse_json(a), _parse_json(b))
    raise ParseError(f"unrecognized JSON node: {obj!r}")


def _parse_nested(s: str, pos: int) -> tuple[Node, int]:
    pos = _skip_ws(s, pos)
    if s.startswith("eml", pos):
        pos = _skip_ws(s, pos + 3)
        if pos >= len(s) or s[pos] != "(":
            raise ParseError(f"expected '(' after 'eml' at {pos}")
        pos = _skip_ws(s, pos + 1)
        a, pos = _parse_nested(s, pos)
        pos = _skip_ws(s, pos)
        if pos >= len(s) or s[pos] != ",":
            raise ParseError(f"expected ',' at {pos}")
        pos = _skip_ws(s, pos + 1)
        b, pos = _parse_nested(s, pos)
        pos = _skip_ws(s, pos)
        if pos >= len(s) or s[pos] != ")":
            raise ParseError(f"expected ')' at {pos}")
        return EmlNode(a, b), pos + 1
    # leaf
    for sym in ("1", "x", "y"):
        if s.startswith(sym, pos):
            return Leaf(sym), pos + len(sym)
    # reject specific non-leaves with a friendly error
    m = re.match(r"[A-Za-z0-9]+", s[pos:])
    if m:
        raise ParseError(
            f"leaf {m.group()!r} not in allowed alphabet {{1, x, y}} (pos {pos})"
        )
    raise ParseError(f"unexpected character {s[pos]!r} at {pos}")


def _skip_ws(s: str, pos: int) -> int:
    while pos < len(s) and s[pos].isspace():
        pos += 1
    return pos


def _parse_rpn(s: str) -> Node:
    # Tokenize. Accept whitespace-separated or concatenated single-char tokens.
    has_ws = any(c.isspace() for c in s)
    tokens: list[str]
    if has_ws:
        tokens = s.split()
    else:
        tokens = list(s)  # single-char alphabet
    stack: list[Node] = []
    for tok in tokens:
        if tok in LEAF_ALPHABET:
            stack.append(Leaf(tok))
        elif tok == "E":
            if len(stack) < 2:
                raise ParseError("RPN: stack underflow at 'E'")
            b = stack.pop()
            a = stack.pop()
            stack.append(EmlNode(a, b))
        else:
            raise ParseError(
                f"RPN token {tok!r} not in {{1, x, y, E}}"
            )
    if len(stack) != 1:
        raise ParseError(f"RPN: expected single root, got {len(stack)} nodes")
    return stack[0]


# ---------- measures ----------


def leaf_counts(ast: Node) -> dict[str, int]:
    counts = {"1": 0, "x": 0, "y": 0}
    _walk_leaves(ast, counts)
    return counts


def _walk_leaves(node: Node, counts: dict[str, int]) -> None:
    if isinstance(node, Leaf):
        counts[node.symbol] += 1
    else:
        _walk_leaves(node.a, counts)
        _walk_leaves(node.b, counts)


def depth(ast: Node) -> int:
    """Binary-tree height. Leaf → 0; eml(Leaf,Leaf) → 1."""
    if isinstance(ast, Leaf):
        return 0
    return 1 + max(depth(ast.a), depth(ast.b))


def k_tokens(ast: Node) -> int:
    """RPN token count: leaves + 'E' operator occurrences."""
    if isinstance(ast, Leaf):
        return 1
    return 1 + k_tokens(ast.a) + k_tokens(ast.b)


def to_rpn(ast: Node) -> str:
    """Canonical space-separated RPN, e.g. eml(x,1) → 'x 1 E'."""
    parts: list[str] = []
    _emit_rpn(ast, parts)
    return " ".join(parts)


def _emit_rpn(node: Node, parts: list[str]) -> None:
    if isinstance(node, Leaf):
        parts.append(node.symbol)
    else:
        _emit_rpn(node.a, parts)
        _emit_rpn(node.b, parts)
        parts.append("E")


# ---------- evaluation ----------


def evaluate(ast: Node, x: complex, y: complex = 1 + 0j) -> complex:
    """Evaluate the tree at (x, y). Uses cmath — principal branch for log."""
    if isinstance(ast, Leaf):
        return _leaf_value(ast.symbol, x, y)
    a = evaluate(ast.a, x, y)
    b = evaluate(ast.b, x, y)
    # eml(a, b) = exp(a) - log(b)   — pinned definition
    return cmath.exp(a) - cmath.log(b)


def _leaf_value(sym: str, x: complex, y: complex) -> complex:
    if sym == "1":
        return 1 + 0j
    if sym == "x":
        return x
    if sym == "y":
        return y
    raise ParseError(f"unknown leaf {sym!r}")
