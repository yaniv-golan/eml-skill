"""Branch-cut probes.

Principal-branch cmath convention. Probes straddle each cut at ±iε to detect
the 2πi jump (or sign flip) that a wrong evaluator would miss.

Cut loci (reminder):
    ln, log10, sqrt : negative real axis (z = -r, r > 0)
    asin, acos      : real axis *outside* [-1, 1] (NOT the unit circle)
    atan            : imaginary axis outside [-i, i] (z = ±it, t > 1)
    exp, sin, cos, poly, add, mult, sub : entire — no cut
"""

from __future__ import annotations

EPS_DEFAULT = 1e-6


def _neg_real_axis(eps: float) -> list[tuple[str, complex]]:
    pts: list[tuple[str, complex]] = []
    for r in (0.1, 1.0, 5.0):
        pts.append(("neg-real-axis", complex(-r, eps)))
        pts.append(("neg-real-axis", complex(-r, -eps)))
    return pts


def _asin_acos_cuts(eps: float) -> list[tuple[str, complex]]:
    pts: list[tuple[str, complex]] = []
    for r in (1.5, 3.0):
        pts.append(("real-axis-outside-[-1,1]", complex(r, eps)))
        pts.append(("real-axis-outside-[-1,1]", complex(r, -eps)))
        pts.append(("real-axis-outside-[-1,1]", complex(-r, eps)))
        pts.append(("real-axis-outside-[-1,1]", complex(-r, -eps)))
    return pts


def _atan_cut(eps: float) -> list[tuple[str, complex]]:
    pts: list[tuple[str, complex]] = []
    for t in (1.5, 3.0):
        pts.append(("imag-axis-outside-[-i,i]", complex(eps, t)))
        pts.append(("imag-axis-outside-[-i,i]", complex(-eps, t)))
        pts.append(("imag-axis-outside-[-i,i]", complex(eps, -t)))
        pts.append(("imag-axis-outside-[-i,i]", complex(-eps, -t)))
    return pts


def probe(claim: str, eps: float = EPS_DEFAULT) -> list[tuple[str, complex]]:
    """Return (locus_label, sample_point) pairs near the claim's branch cuts.

    Empty list for entire functions (exp, sin, cos, poly, add, mult, sub).
    """
    if claim in ("ln", "log10", "sqrt"):
        return _neg_real_axis(eps)
    if claim in ("asin", "acos"):
        return _asin_acos_cuts(eps)
    if claim == "atan":
        return _atan_cut(eps)
    return []
