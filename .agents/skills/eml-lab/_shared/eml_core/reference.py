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
    "neg": lambda x, _y: -x,
    "inv": lambda x, _y: 1 / x,
    # binary in (x, y)
    "add": lambda x, y: x + y,
    "sub": lambda x, y: x - y,
    "mult": lambda x, y: x * y,
    "div": lambda x, y: x / y,
    "pow": lambda x, y: cmath.exp(y * cmath.log(x)),
    # constants (ignore both args)
    "e": lambda _x, _y: complex(cmath.e, 0),
    "pi": lambda _x, _y: complex(cmath.pi, 0),
    "i": lambda _x, _y: 1j,
}


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
    return claim in ("add", "sub", "mult", "div", "pow")
