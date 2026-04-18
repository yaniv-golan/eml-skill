"""Extended-reals evaluator for EML trees.

Reproduces the paper's (arXiv:2603.21852) direct-search semantics, which
treats ±∞ as a value rather than an exception. Under this regime:

    log(0 + 0j)  = complex(-inf, 0)           # vs cmath: ValueError
    log(-0 + 0j) = complex(-inf, 0)           # vs cmath: -inf + i·π
    exp(-inf)    = 0 + 0j                     # same as cmath
    exp(+inf)    = complex(+inf, 0)           # same as cmath
    log(±inf)    = complex(+inf, 0)           # same as cmath

The evaluator is *additive only* — it does not replace, monkey-patch, or
shadow the default `cmath`-based `eml_core.eml.evaluate`. Call sites that
need the paper's extended-reals K=15 reproductions opt in explicitly.

All arithmetic uses sentinel-guarded Python floats (`math.inf`, `-math.inf`)
so that intermediate `+inf − +inf` collisions surface as `nan` and
downstream comparisons return `False`, exactly as the paper's direct-search
tooling reports them.

References:
- `docs/refutation-neg-inv-k15.md` §"Audit — extended reals (2026-04-19)"
- `docs/extended-reals-evaluator-2026-04-19.md`
- user-memory fact `project_neg_inv_k15_extended_reals`.
"""

from __future__ import annotations

import cmath
import math
from typing import Callable

from .eml import EmlNode, Leaf, Node, parse

__all__ = [
    "evaluate_extended",
    "eml_extended",
    "log_extended",
    "exp_extended",
    "extended_reference",
]


# ---------- primitive operators ----------

def log_extended(z: complex) -> complex:
    """`log` with extended-reals semantics on the zero input.

    The only divergence from `cmath.log`:
      - `log(0 + 0j)` and `log(-0 + 0j)` both return `complex(-inf, 0)`.
        Under `cmath`, the first raises `ValueError`, and the second returns
        `-inf + i·π` (principal branch of `log(-1) = i·π` in the limit).

    Every other input — finite nonzero, ±∞, i·finite, NaN — falls through
    to `cmath.log`, which already handles ±∞ magnitudes correctly
    (`cmath.log(inf + 0j) = inf + 0j`).
    """
    z = complex(z)
    if z.real == 0.0 and z.imag == 0.0:
        return complex(-math.inf, 0.0)
    return cmath.log(z)


def exp_extended(z: complex) -> complex:
    """`exp` with sentinel handling for real infinities.

    Matches `cmath.exp` on every finite input and on `±inf + 0j`. Exposed
    as a named function so the semantics are documented in one place and
    so `evaluate_extended` has a single operator to test.
    """
    z = complex(z)
    # cmath already returns 0+0j for exp(-inf+0j) and inf+0j for exp(+inf+0j).
    # Guard only the exotic `-inf + i·finite` case, which cmath returns as
    # `0*cos(finite) - 0j*sin(finite)` — fine, but lossy on signs. We keep
    # cmath's answer for continuity with the default evaluator.
    return cmath.exp(z)


def eml_extended(a: complex, b: complex) -> complex:
    """Extended-reals EML: `exp_extended(a) - log_extended(b)`.

    Subtraction uses Python's native complex arithmetic. The infinity
    arithmetic collapses cleanly on pure-real ±∞ operands:
      `finite − (−inf) = +inf`, `finite − (+inf) = −inf`,
      `(+inf) − (+inf) = nan + 0j` (IEEE).
    This last case is the only numerical pitfall; tests that expect a
    specific numeric limit should phrase that limit explicitly rather than
    leaning on `nan` cancelling later.
    """
    return exp_extended(a) - log_extended(b)


# ---------- tree evaluator ----------

def evaluate_extended(ast: Node, x: complex, y: complex = 1 + 0j) -> complex:
    """Evaluate an EML tree under extended-reals semantics.

    Parallel to `eml_core.eml.evaluate`, but every internal `eml(a, b)`
    node routes through `eml_extended` so `log(0)` intermediates are
    permitted as `-inf`. Leaf evaluation is identical to the default
    evaluator — leaves {1, x, y} are never infinite at construction.
    """
    if isinstance(ast, Leaf):
        if ast.symbol == "1":
            return 1 + 0j
        if ast.symbol == "x":
            return x
        if ast.symbol == "y":
            return y
        raise ValueError(f"unknown leaf {ast.symbol!r}")
    a = evaluate_extended(ast.a, x, y)
    b = evaluate_extended(ast.b, x, y)
    return eml_extended(a, b)


# ---------- reference wrapper ----------

Ref = Callable[[complex, complex], complex]


def extended_reference(tree: str | Node) -> Ref:
    """Wrap a tree (string or AST) as a reference callable `f(x, y)`.

    Use this when you want to compare a claimed extended-reals tree
    against another extended-reals tree, or against a paper claim
    evaluated in the extended-reals regime.
    """
    ast = parse(tree) if isinstance(tree, str) else tree
    return lambda x, y=1 + 0j: evaluate_extended(ast, x, y)


# ---------- paper K=15 reproductions (extended reals) ----------

# Canonical K=15 trees for `neg` and `inv`. Both share an 11-token "A"
# subtree that passes through `log(0) = -inf`. Copied (trees only) from
# `docs/refutation-neg-inv-k15.md` §"Extended-reals witness (K=15)".
#
# Exposed as constants so tests and docs can import them by name without
# re-parsing the document.

NEG_K15_EXTENDED = (
    "eml(eml(1, eml(1, eml(1, eml(eml(1, 1), 1)))), eml(x, 1))"
)
INV_K15_EXTENDED = (
    "eml(eml(eml(1, eml(1, eml(1, eml(eml(1, 1), 1)))), x), 1)"
)
# `minus_one(0.5) = neg(1)`: substitute the `x` leaf in NEG_K15_EXTENDED
# with `1`. Same K=15 (the substituted leaf is replaced by another leaf,
# no token-count change). Confirms the paper Table 4 row `-1: 15 (17)`:
# K=15 under extended reals, K=17 without — the value 17 matches the
# shipped IEEE witness.
MINUS_ONE_K15_EXTENDED = (
    "eml(eml(1, eml(1, eml(1, eml(eml(1, 1), 1)))), eml(1, 1))"
)
