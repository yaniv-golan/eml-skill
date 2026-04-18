"""Claim name → reference function (Callable[[complex, complex], complex]).

Every reference uses cmath (principal branch). The audit tool uses these to
numerically verify a claimed EML tree.
"""

from __future__ import annotations

import cmath
from typing import Callable

Ref = Callable[[complex, complex], complex]


class ReferenceResolveError(ValueError):
    """Raised when a claim name has no reference function."""


def _log10(x: complex, _y: complex) -> complex:
    return cmath.log(x) / cmath.log(10)


NAMED_CLAIMS: dict[str, Ref] = {
    # unary-in-x
    "exp": lambda x, _y: cmath.exp(x),
    "ln": lambda x, _y: cmath.log(x),
    "log10": _log10,
    "sqrt": lambda x, _y: cmath.sqrt(x),
    "sin": lambda x, _y: cmath.sin(x),
    "cos": lambda x, _y: cmath.cos(x),
    "tan": lambda x, _y: cmath.tan(x),
    "asin": lambda x, _y: cmath.asin(x),
    "acos": lambda x, _y: cmath.acos(x),
    "atan": lambda x, _y: cmath.atan(x),
    "sinh": lambda x, _y: cmath.sinh(x),
    "cosh": lambda x, _y: cmath.cosh(x),
    "tanh": lambda x, _y: cmath.tanh(x),
    "asinh": lambda x, _y: cmath.asinh(x),
    "acosh": lambda x, _y: cmath.acosh(x),
    "atanh": lambda x, _y: cmath.atanh(x),
    "neg": lambda x, _y: -x,
    "inv": lambda x, _y: 1 / x,
    # specialized unary (arXiv:2603.21852 Table 4 direct-search harvest):
    "sq": lambda x, _y: x * x,
    "succ": lambda x, _y: x + 1,
    "pred": lambda x, _y: x - 1,
    "double": lambda x, _y: 2 * x,
    "half": lambda x, _y: x / 2,
    # binary in (x, y)
    "add": lambda x, y: x + y,
    "sub": lambda x, y: x - y,
    "mult": lambda x, y: x * y,
    "div": lambda x, y: x / y,
    "pow": lambda x, y: cmath.exp(y * cmath.log(x)),
    "log_x_y": lambda x, y: cmath.log(y) / cmath.log(x),
    "avg": lambda x, y: (x + y) / 2,
    "hypot": lambda x, y: cmath.sqrt(x * x + y * y),
    # constants (ignore both args)
    "e": lambda _x, _y: complex(cmath.e, 0),
    "pi": lambda _x, _y: complex(cmath.pi, 0),
    "i": lambda _x, _y: 1j,
    # Table-4 arity-0 harvest (2026-04-19): named small integers + half.
    # See `docs/paper-table4-coverage-audit-2026-04-19.md` for provenance.
    "zero": lambda _x, _y: 0 + 0j,
    "minus_one": lambda _x, _y: -1 + 0j,
    "two": lambda _x, _y: 2 + 0j,
    "half_const": lambda _x, _y: 0.5 + 0j,
}


# Constants that take no meaningful arguments (both x and y are ignored).
# Used by downstream tooling (e.g. equivalence_check, branch_audit) to skip
# interior-sampling / branch-probe work that only makes sense for non-constants.
_CONSTANT_CLAIMS: frozenset[str] = frozenset(
    {"e", "pi", "i", "zero", "minus_one", "two", "half_const"}
)


def is_constant(claim: str) -> bool:
    """True if the reference is arity-0 (ignores both x and y)."""
    return claim in _CONSTANT_CLAIMS


def resolve(claim: str) -> Ref:
    """Resolve a claim name to a reference function.

    Named table first. Ad-hoc formulas (e.g. 'x + sin(y)') are intentionally
    not supported in iteration-2 — add via sympy later if the need is real.
    """
    if claim in NAMED_CLAIMS:
        return NAMED_CLAIMS[claim]
    raise ReferenceResolveError(
        f"unknown claim {claim!r}; known: {sorted(NAMED_CLAIMS)}"
    )


def is_binary(claim: str) -> bool:
    """True if the reference genuinely uses y (vs. unary or constant)."""
    return claim in ("add", "sub", "mult", "div", "pow", "log_x_y", "avg", "hypot")


def is_constant(claim: str) -> bool:
    """True if the reference uses neither x nor y (arity-0 constants)."""
    return claim in ("e", "pi", "i")
