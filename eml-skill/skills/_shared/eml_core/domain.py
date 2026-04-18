"""Domain samplers. Named domains → list[complex].

Interior sampling deliberately avoids boundaries so the multiplication tree's
removable singularity at xy=0 doesn't pollute max_abs_diff.
"""

from __future__ import annotations

import cmath
import math
import random
import sys
from typing import Callable, Iterable, Optional

Sampler = Callable[[int, random.Random], list[complex]]


def _positive_reals(n: int, rng: random.Random) -> list[complex]:
    # log-uniform on [1e-3, 50], strictly positive real.
    #
    # Upper bound tightened from 1e3 → 50 in P1.1-followup-3. Rationale:
    # witness trees built on `exp(x)` (e.g. the ADD K=19 tree
    # `eml(ln(exp(x)+exp(y)), 1)`) overflow float64 when x ≳ 709. The old
    # upper bound of 1e3 put ~50% of samples above that threshold and caused
    # `OverflowError` during audit. `exp(50) ≈ 5.2e21` is comfortably below
    # the float64 limit `exp(709) ≈ 8.2e307` while still spanning ~5 decades
    # of magnitude on the upper end — ample coverage for witness behavior
    # across small/large positive reals. 100+ was rejected because
    # `exp(100) ≈ 2.7e43` pushes `ln(1+ε)` precision into degradation.
    lo, hi = math.log(1e-3), math.log(50)
    return [complex(math.exp(lo + (hi - lo) * rng.random()), 0.0) for _ in range(n)]


def _real_interval(n: int, rng: random.Random) -> list[complex]:
    # (-3, 3) strictly interior
    return [complex(-3 + 6 * rng.random(), 0.0) for _ in range(n)]


def _complex_box(n: int, rng: random.Random) -> list[complex]:
    # Re, Im ∈ (-2, 2)
    return [complex(-2 + 4 * rng.random(), -2 + 4 * rng.random()) for _ in range(n)]


def _unit_disk_interior(n: int, rng: random.Random) -> list[complex]:
    # |z| strictly < 0.9 (avoid boundary for asin/acos)
    pts: list[complex] = []
    while len(pts) < n:
        z = complex(-1 + 2 * rng.random(), -1 + 2 * rng.random())
        if abs(z) < 0.9:
            pts.append(z)
    return pts


def _right_half_plane(n: int, rng: random.Random) -> list[complex]:
    # Re(z) > 0.1, |Im(z)| < 2
    return [complex(0.1 + 3 * rng.random(), -2 + 4 * rng.random()) for _ in range(n)]


DOMAIN_SAMPLERS: dict[str, Sampler] = {
    "positive-reals": _positive_reals,
    "real-interval": _real_interval,
    "complex-box": _complex_box,
    "unit-disk-interior": _unit_disk_interior,
    "right-half-plane": _right_half_plane,
}


def sample(name: str, n: int, seed: int = 0) -> list[complex]:
    if name not in DOMAIN_SAMPLERS:
        raise ValueError(f"unknown domain {name!r}; known: {sorted(DOMAIN_SAMPLERS)}")
    rng = random.Random(seed)
    return DOMAIN_SAMPLERS[name](n, rng)


# Named claim → natural domain for its reference function.
_CLAIM_DOMAIN = {
    "ln": "positive-reals",
    "log10": "positive-reals",
    "sqrt": "positive-reals",
    "asin": "unit-disk-interior",
    "acos": "unit-disk-interior",
    "atan": "real-interval",
    "sinh": "real-interval",
    "cosh": "real-interval",
    "tanh": "unit-disk-interior",
    "asinh": "real-interval",
    "acosh": "positive-reals",
    "atanh": "unit-disk-interior",
    "exp": "complex-box",
    "sin": "complex-box",
    "cos": "complex-box",
    "tan": "real-interval",
    "add": "complex-box",
    "mult": "complex-box",
    "sub": "complex-box",
    "div": "right-half-plane",
    "pow": "right-half-plane",
    "neg": "real-interval",
    "inv": "right-half-plane",
}


def auto_domain_for(claim: str) -> str:
    return _CLAIM_DOMAIN.get(claim, "real-interval")


# ---------------------------------------------------------------------------
# Autodetect a safe default domain from a compile's `used_witnesses` list.
#
# Motivation: P3.1 confirmed that the `add` witness genuinely fails on
# `complex-box` (max_diff = 2π on that domain) even though its declared
# natural domain is `positive-reals`. If compile-render defaults --domain to
# complex-box for every expression, any use of the add witness reports
# spurious audit failures that are actually domain-declaration mismatches.
#
# Narrowing priority (most restrictive wins):
#   1. positive-reals
#   2. unit-disk-interior
#   3. complex-box
#
# Empty used_witnesses → fallback "complex-box" (no witness-imposed constraint).
# Unknown domain string → safe fallback "positive-reals" + stderr warning.
# ---------------------------------------------------------------------------

_NARROW_ORDER: tuple[str, ...] = (
    "positive-reals",
    "unit-disk-interior",
    "complex-box",
)


# Witness tree → safe *evaluation* domain. This is distinct from `_CLAIM_DOMAIN`
# above (which is the *reference function's* natural domain, used by
# `/eml-check` via `auto_domain_for`). The distinction matters because some
# witness trees have stricter safe-evaluation domains than their reference
# functions: e.g. `add`'s witness tree is built from `ln(exp(x)*exp(y))` and
# inherits `ln`'s positive-reals requirement, even though mathematical
# addition is defined on all of C. P3.1 quantified this: the existing K=19
# ADD tree genuinely fails on complex-box with max_diff = 2π. Keeping this
# separate from _CLAIM_DOMAIN avoids breaking `/eml-check`'s existing
# claim-driven domain selection while letting `_autodetect_domain` pick a
# safe audit domain in `/eml-lab compile-render`.
_WITNESS_SAFE_DOMAIN: dict[str, str] = {
    # axioms / unary in 1 arg
    "e": "complex-box",
    "exp": "complex-box",
    "ln": "positive-reals",
    "log10": "positive-reals",
    "sqrt": "positive-reals",
    # trig forward (harvested identity trees; the reference is entire, and
    # harvested trees are valid on complex-box too)
    "sin": "complex-box",
    "cos": "complex-box",
    "tan": "complex-box",
    # inverse trig: bounded to the principal sheet's interior
    "asin": "unit-disk-interior",
    "acos": "unit-disk-interior",
    "atan": "unit-disk-interior",
    # hyperbolic forward (composed from exp / add / sub / inv; inherit the
    # add/sub witnesses' positive-reals constraint — the composite trees only
    # hold on real-interval or unit-disk-interior for complex inputs, but
    # positive-reals is the safest narrowing-lattice member. Keep at
    # positive-reals to match the arithmetic-primitive pattern.)
    "sinh": "positive-reals",
    "cosh": "positive-reals",
    "tanh": "positive-reals",
    # inverse hyperbolic: composed trees inherit add/sub/ln constraints.
    "asinh": "positive-reals",
    "acosh": "positive-reals",
    "atanh": "positive-reals",
    # arithmetic primitives: trees built on ln/exp compositions inherit
    # ln's positive-reals constraint (P3.1-quantified for add at max_diff=2π)
    "add": "positive-reals",
    "sub": "positive-reals",
    "mult": "positive-reals",
    "div": "positive-reals",
    "pow": "positive-reals",
    "neg": "positive-reals",
    "inv": "positive-reals",
}


def _witness_domain(name: str) -> Optional[str]:
    """Return the declared safe-evaluation domain for a witness name, or None.

    The `Witness` dataclass itself does not carry a domain field (WITNESSES is
    append-only per CLAUDE.md); the name → safe-domain map lives in this
    module as `_WITNESS_SAFE_DOMAIN`. Returning None means the witness has no
    registered safe-domain and should contribute nothing to narrowing.
    """
    return _WITNESS_SAFE_DOMAIN.get(name)


def _autodetect_domain(
    used_witnesses: Iterable[str],
    *,
    stderr=None,
) -> str:
    """Return the narrowest safe sampling domain for a set of used witnesses.

    Narrowing rule (most restrictive wins, in this priority order):
        positive-reals > unit-disk-interior > complex-box

    Unknown domain strings (anything not in `_NARROW_ORDER`) are treated as
    "unknown, fall back to positive-reals" with a stderr warning. Empty input
    falls back to `complex-box` (no witness-imposed constraint).

    `stderr` is injected for test observability; defaults to `sys.stderr`.
    """
    if stderr is None:
        stderr = sys.stderr

    names = list(used_witnesses)
    if not names:
        return "complex-box"

    domains: set[str] = set()
    unknown_found = False
    for n in names:
        d = _witness_domain(n)
        if d is None:
            continue
        if d in _NARROW_ORDER:
            domains.add(d)
        else:
            # Witness declares a domain outside the narrowing lattice (e.g.
            # `real-interval`, `right-half-plane`). Safe-by-default: narrow to
            # positive-reals and warn once.
            unknown_found = True
            print(
                f"# warn: witness domain {d!r} not in narrowing lattice "
                f"{_NARROW_ORDER}; falling back to 'positive-reals'",
                file=stderr,
            )

    if unknown_found:
        return "positive-reals"

    if not domains:
        # witnesses present but none declared a domain we recognize
        return "complex-box"

    for candidate in _NARROW_ORDER:
        if candidate in domains:
            return candidate

    # Unreachable given the filter above, but keep the safe default.
    return "complex-box"  # pragma: no cover
