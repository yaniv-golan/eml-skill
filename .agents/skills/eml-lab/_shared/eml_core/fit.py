"""Library-first regression: rank library witnesses by fit quality on (x, y) data.

Modes:
- Unary (2-col): rank each arity-1 witness by max |y - w(x)|.
- Affine (2-col, opt-in): fit y ≈ a·w(x) + b; snap a, b to recognized constants.
- Binary (3-col x, y, z): rank each arity-2 witness by max |z - w(x, y)|.

All evaluation uses cmath (principal branch).
"""

from __future__ import annotations

import cmath
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .reference import NAMED_CLAIMS, is_binary
from .witnesses import WITNESSES

_UNARY_CANDIDATES = tuple(
    name
    for name in WITNESSES
    if WITNESSES[name].arity == 1 and name in NAMED_CLAIMS
)
_BINARY_CANDIDATES = ("add", "sub", "mult", "div", "pow")


# Recognized constants for snap. Name → numeric value.
# Include common multiples/inverses; snapper returns the best (closest) name.
_KNOWN_CONSTANTS: dict[str, complex] = {
    "0": complex(0, 0),
    "1": complex(1, 0),
    "-1": complex(-1, 0),
    "2": complex(2, 0),
    "-2": complex(-2, 0),
    "3": complex(3, 0),
    "-3": complex(-3, 0),
    "1/2": complex(0.5, 0),
    "1/3": complex(1 / 3, 0),
    "pi": complex(cmath.pi, 0),
    "-pi": complex(-cmath.pi, 0),
    "pi/2": complex(cmath.pi / 2, 0),
    "pi/3": complex(cmath.pi / 3, 0),
    "pi/4": complex(cmath.pi / 4, 0),
    "2*pi": complex(2 * cmath.pi, 0),
    "1/pi": complex(1 / cmath.pi, 0),
    "e": complex(cmath.e, 0),
    "-e": complex(-cmath.e, 0),
    "1/e": complex(1 / cmath.e, 0),
    "ln(2)": complex(cmath.log(2).real, 0),
    "ln(10)": complex(cmath.log(10).real, 0),
    "1/ln(10)": complex(1 / cmath.log(10).real, 0),
    "sqrt(2)": complex(cmath.sqrt(2).real, 0),
    "i": 1j,
    # iter-7: out-of-table constants surfaced by iter-6 evals
    "G_catalan": complex(0.9159655941772190, 0),
    "zeta(3)": complex(1.2020569031595943, 0),
    "K_khinchin": complex(2.6854520010653064, 0),
    "log2(e)": complex(1.4426950408889634, 0),  # = 1/ln(2)
    "e^pi": complex(23.140692632779267, 0),  # Gelfond's constant
    "gamma": complex(0.5772156649015329, 0),  # Euler-Mascheroni
}


class FitError(ValueError):
    """Raised on malformed CSV or inconsistent column counts."""


@dataclass
class FitResult:
    name: str
    max_abs_residual: float
    mean_abs_residual: float
    r_squared: float
    verified: bool
    n_samples: int
    n_errors: int


@dataclass
class AffineFit:
    """y ≈ a · w(x) + b, evaluated against library witness `name`."""
    name: str
    a: complex
    b: complex
    a_snapped: str | None  # name of recognized constant, if |a - c| <= snap_tol
    b_snapped: str | None
    max_abs_residual: float
    mean_abs_residual: float
    r_squared: float
    verified: bool
    n_samples: int
    n_errors: int
    # Standard errors (populated when noise_sigma is provided to fit_affine).
    se_a: float | None = None
    se_b: float | None = None
    snap_tol_used: float | None = None
    tolerance_used: float | None = None


@dataclass
class CompositeFit:
    """y ≈ w(v(x)) for unary primitives w, v."""
    outer: str
    inner: str
    max_abs_residual: float
    mean_abs_residual: float
    r_squared: float
    verified: bool
    n_samples: int
    n_errors: int

    @property
    def name(self) -> str:
        return f"{self.outer}({self.inner}(x))"


def load_csv(path: Path) -> list[list[complex]]:
    """Load a CSV and return column-major complex lists.

    Handles 2-col (x, y) and 3-col (x, y, z). First row may be a header
    (auto-detected: if the first cell fails to parse as complex, skip it).
    """
    rows: list[list[str]] = []
    with path.open() as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            rows.append([c.strip() for c in row])
    if not rows:
        raise FitError(f"{path}: empty CSV")
    try:
        _parse_complex(rows[0][0])
        data_rows = rows
    except (ValueError, IndexError):
        data_rows = rows[1:]
    if not data_rows:
        raise FitError(f"{path}: no data rows")
    ncols = len(data_rows[0])
    if ncols not in (2, 3):
        raise FitError(f"{path}: expected 2 or 3 columns, got {ncols}")
    cols: list[list[complex]] = [[] for _ in range(ncols)]
    for i, row in enumerate(data_rows):
        if len(row) < ncols:
            raise FitError(f"{path}: row {i} has fewer than {ncols} columns")
        for k in range(ncols):
            cols[k].append(_parse_complex(row[k]))
    return cols


def load_xy_csv(path: Path) -> tuple[list[complex], list[complex]]:
    """Backward-compatible 2-column loader."""
    cols = load_csv(path)
    if len(cols) != 2:
        raise FitError(f"{path}: expected 2 columns, got {len(cols)}")
    return cols[0], cols[1]


def _parse_complex(s: str) -> complex:
    s = s.strip()
    try:
        return complex(float(s))
    except ValueError:
        pass
    try:
        return complex(s.replace(" ", ""))
    except ValueError as e:
        raise ValueError(f"cannot parse complex number: {s!r}") from e


def fit_unary(
    xs: list[complex],
    ys: list[complex],
    tolerance: float = 1e-6,
    candidates: Iterable[str] | None = None,
) -> list[FitResult]:
    """Rank unary library witnesses by max |y - w(x)|. Ascending residual."""
    if len(xs) != len(ys):
        raise FitError(f"xs/ys length mismatch: {len(xs)} vs {len(ys)}")
    if not xs:
        raise FitError("empty dataset")

    names = tuple(candidates) if candidates is not None else _UNARY_CANDIDATES
    y_mean = sum(ys) / len(ys)
    ss_tot = sum(abs(y - y_mean) ** 2 for y in ys) or float("inf")

    results: list[FitResult] = []
    for name in names:
        if name not in NAMED_CLAIMS or is_binary(name):
            continue
        ref = NAMED_CLAIMS[name]
        residuals: list[float] = []
        n_errors = 0
        ss_res = 0.0
        for x, y in zip(xs, ys):
            try:
                pred = ref(x, complex(0))
                r = abs(y - pred)
                residuals.append(r)
                ss_res += r * r
            except (ZeroDivisionError, ValueError, OverflowError):
                n_errors += 1
                residuals.append(float("inf"))
                ss_res = float("inf")
        max_r = max(residuals) if residuals else float("inf")
        mean_r = (
            sum(r for r in residuals if r != float("inf")) / max(1, len(residuals) - n_errors)
            if n_errors < len(residuals)
            else float("inf")
        )
        r2 = 1.0 - ss_res / ss_tot if ss_tot != float("inf") and ss_res != float("inf") else float("-inf")
        results.append(
            FitResult(
                name=name,
                max_abs_residual=max_r,
                mean_abs_residual=mean_r,
                r_squared=r2,
                verified=max_r <= tolerance,
                n_samples=len(xs),
                n_errors=n_errors,
            )
        )
    results.sort(key=lambda r: (r.max_abs_residual, -r.r_squared))
    return results


def fit_binary(
    xs: list[complex],
    ys: list[complex],
    zs: list[complex],
    tolerance: float = 1e-6,
    candidates: Iterable[str] | None = None,
) -> list[FitResult]:
    """Rank binary library witnesses by max |z - w(x, y)|. Ascending residual."""
    if not (len(xs) == len(ys) == len(zs)):
        raise FitError(f"xs/ys/zs length mismatch: {len(xs)}/{len(ys)}/{len(zs)}")
    if not xs:
        raise FitError("empty dataset")

    names = tuple(candidates) if candidates is not None else _BINARY_CANDIDATES
    z_mean = sum(zs) / len(zs)
    ss_tot = sum(abs(z - z_mean) ** 2 for z in zs) or float("inf")

    results: list[FitResult] = []
    for name in names:
        if name not in NAMED_CLAIMS or not is_binary(name):
            continue
        ref = NAMED_CLAIMS[name]
        residuals: list[float] = []
        n_errors = 0
        ss_res = 0.0
        for x, y, z in zip(xs, ys, zs):
            try:
                pred = ref(x, y)
                r = abs(z - pred)
                residuals.append(r)
                ss_res += r * r
            except (ZeroDivisionError, ValueError, OverflowError):
                n_errors += 1
                residuals.append(float("inf"))
                ss_res = float("inf")
        max_r = max(residuals) if residuals else float("inf")
        mean_r = (
            sum(r for r in residuals if r != float("inf")) / max(1, len(residuals) - n_errors)
            if n_errors < len(residuals)
            else float("inf")
        )
        r2 = 1.0 - ss_res / ss_tot if ss_tot != float("inf") and ss_res != float("inf") else float("-inf")
        results.append(
            FitResult(
                name=name,
                max_abs_residual=max_r,
                mean_abs_residual=mean_r,
                r_squared=r2,
                verified=max_r <= tolerance,
                n_samples=len(xs),
                n_errors=n_errors,
            )
        )
    results.sort(key=lambda r: (r.max_abs_residual, -r.r_squared))
    return results


def _snap_constant(value: complex, snap_tol: float) -> str | None:
    """Return the name of the closest recognized constant within snap_tol, else None."""
    best: tuple[float, str] | None = None
    for name, c in _KNOWN_CONSTANTS.items():
        d = abs(value - c)
        if d <= snap_tol and (best is None or d < best[0]):
            best = (d, name)
    return best[1] if best else None


def fit_affine(
    xs: list[complex],
    ys: list[complex],
    tolerance: float = 1e-6,
    snap_tol: float = 1e-4,
    candidates: Iterable[str] | None = None,
    noise_sigma: float | None = None,
) -> list[AffineFit]:
    """For each unary witness w, fit y ≈ a·w(x) + b (complex least-squares).

    Snap a, b to recognized constants if within snap_tol. Rank by ascending
    max residual of the affine prediction.

    `noise_sigma`: if the user supplies an estimated per-sample noise stdev,
    auto-loosen `tolerance` and `snap_tol` so a perfect-but-noisy fit isn't
    rejected and so coefficients within the noise floor still snap. Reports
    SE(a), SE(b) on each fit.
    """
    if len(xs) != len(ys):
        raise FitError(f"xs/ys length mismatch: {len(xs)} vs {len(ys)}")
    if not xs:
        raise FitError("empty dataset")

    names = tuple(candidates) if candidates is not None else _UNARY_CANDIDATES
    n = len(xs)

    # Noise-aware thresholds: 3σ for "verified" (one-sample tail), and snap
    # tolerance scaled by 3σ/√n (rough SE of the mean).
    if noise_sigma is not None and noise_sigma > 0:
        tolerance = max(tolerance, 3.0 * noise_sigma)
        snap_tol = max(snap_tol, 3.0 * noise_sigma / cmath.sqrt(n).real)

    results: list[AffineFit] = []
    for name in names:
        if name not in NAMED_CLAIMS or is_binary(name):
            continue
        ref = NAMED_CLAIMS[name]
        # Evaluate w(x) for each sample; skip witness entirely if any domain
        # error in the support (iter-2 keeps affine clean — one bad sample
        # disqualifies the witness rather than silently averaging).
        ws: list[complex] = []
        n_errors = 0
        try:
            for x in xs:
                ws.append(ref(x, complex(0)))
        except (ZeroDivisionError, ValueError, OverflowError):
            n_errors = 1
            results.append(AffineFit(
                name=name, a=complex(0), b=complex(0),
                a_snapped=None, b_snapped=None,
                max_abs_residual=float("inf"),
                mean_abs_residual=float("inf"),
                r_squared=float("-inf"),
                verified=False, n_samples=n, n_errors=n_errors,
                se_a=None, se_b=None,
                snap_tol_used=snap_tol, tolerance_used=tolerance,
            ))
            continue

        # Solve the 2x2 complex normal equations for [a, b]:
        #   [sum|w|^2, sum conj(w) ]   [a]   [sum conj(w) * y]
        #   [sum w,    N            ]   [b] = [sum y]
        sw = sum(ws)
        sw_conj = sum(w.conjugate() for w in ws)
        sww = sum(abs(w) ** 2 for w in ws)
        sy = sum(ys)
        swy = sum(w.conjugate() * y for w, y in zip(ws, ys))
        # Matrix [[sww, sw_conj], [sw, N]] · [a, b] = [swy, sy]
        det = sww * n - sw_conj * sw
        if abs(det) < 1e-30:
            # Degenerate (e.g. w is constant) — fall back to b = mean(y), a = 0
            a = complex(0, 0)
            b = sy / n
        else:
            a = (swy * n - sw_conj * sy) / det
            b = (sww * sy - sw * swy) / det

        # Residuals with (a, b).
        residuals = [abs(y - (a * w + b)) for w, y in zip(ws, ys)]
        max_r = max(residuals)
        mean_r = sum(residuals) / n
        y_mean = sy / n
        ss_tot = sum(abs(y - y_mean) ** 2 for y in ys) or float("inf")
        ss_res = sum(r * r for r in residuals)
        r2 = 1.0 - ss_res / ss_tot if ss_tot != float("inf") else float("-inf")

        # Standard errors. Use noise_sigma if given, else residual stdev.
        # SE^2 propagates the inverse normal-matrix diagonal:
        #   var(a) = sigma^2 * N / |det|,  var(b) = sigma^2 * sww / |det|.
        se_a: float | None = None
        se_b: float | None = None
        if abs(det) >= 1e-30:
            if noise_sigma is not None and noise_sigma > 0:
                sigma2 = noise_sigma * noise_sigma
            elif n > 2:
                sigma2 = ss_res / (n - 2)
            else:
                sigma2 = 0.0
            inv_det = 1.0 / abs(det)
            se_a = float(cmath.sqrt(sigma2 * n * inv_det).real)
            se_b = float(cmath.sqrt(sigma2 * sww * inv_det).real)

        a_snap = _snap_constant(a, snap_tol)
        b_snap = _snap_constant(b, snap_tol)

        results.append(AffineFit(
            name=name, a=a, b=b,
            a_snapped=a_snap, b_snapped=b_snap,
            max_abs_residual=max_r,
            mean_abs_residual=mean_r,
            r_squared=r2,
            verified=max_r <= tolerance,
            n_samples=n, n_errors=0,
            se_a=se_a, se_b=se_b,
            snap_tol_used=snap_tol, tolerance_used=tolerance,
        ))
    results.sort(key=lambda r: (r.max_abs_residual, -r.r_squared))
    return results


def diagnose_affine_hint(
    xs: list[complex],
    ys: list[complex],
    affine_results: list[AffineFit],
) -> str | None:
    """Inspect the best affine candidate's residuals and return a one-line hint
    suggesting a richer hypothesis class — or None if no clear pattern.

    Triggered only when *no* affine candidate verified. Heuristics (cheap,
    no FFT, intended for ~10-1000 row CSVs):

    * sin/cos best candidate with residual showing sign-flip oscillation above
      an ambient threshold → scale-x composite (e.g. y = a·sin(b·x) + c).
    * exp/ln best candidate with monotonic residual vs. x → composite-inside-
      the-argument (e.g. y = a·exp(b·x) + c).

    The hint is purely advisory; it never changes the verdict.
    """
    # Only hint when nothing matched. A verified fit speaks for itself.
    if not affine_results or any(r.verified for r in affine_results):
        return None

    # Best candidate by ranked order (already ascending max_abs_residual).
    best = affine_results[0]
    ref = NAMED_CLAIMS.get(best.name)
    if ref is None:
        return None

    # Recompute residuals with the fitted a, b. We need the signed residual
    # on the real axis to look for sign flips; bail out if w(x) errored or
    # ys have non-trivial imaginary parts (real-valued oscillation check).
    try:
        preds = [best.a * ref(x, complex(0)) + best.b for x in xs]
    except (ZeroDivisionError, ValueError, OverflowError):
        return None
    residuals_real = [(y - p).real for y, p in zip(ys, preds)]
    n = len(residuals_real)
    if n < 6:
        return None

    # Ambient scale: mean |residual|. Used to mask near-zero crossings so
    # tiny numerical wobble doesn't register as an oscillation.
    mean_abs = sum(abs(r) for r in residuals_real) / n
    if mean_abs <= 1e-12:
        return None

    # Sign-flip count over samples whose |residual| exceeds a fraction of the
    # ambient scale. Many flips with material amplitude = periodic structure.
    threshold = 0.1 * mean_abs
    sign_flips = 0
    last_sign = 0
    for r in residuals_real:
        if abs(r) < threshold:
            continue
        s = 1 if r > 0 else -1
        if last_sign != 0 and s != last_sign:
            sign_flips += 1
        last_sign = s

    # Oscillation hint: for a pure scale-x miss like y = 2·sin(3·x) fitted by
    # a·sin(x), the residual flips sign many times across the window. A
    # conservative floor of 4 flips rules out a single bend from a bad
    # monotone fit.
    periodic_like = best.name in ("sin", "cos")
    if periodic_like and sign_flips >= 4:
        return (
            "residual shows periodicity — try a scale-x composite like "
            "y = a*sin(b*x) + c; --affine cannot fit scale-x"
        )

    # Monotonicity hint for exp/ln misses: if residuals are (mostly) monotonic
    # in x, the missing factor is likely inside the argument.
    if best.name in ("exp", "ln"):
        # Sort by real(x) then count strict monotone steps.
        order = sorted(range(n), key=lambda i: xs[i].real)
        sorted_res = [residuals_real[i] for i in order]
        ups = sum(1 for a, b in zip(sorted_res, sorted_res[1:]) if b > a)
        downs = sum(1 for a, b in zip(sorted_res, sorted_res[1:]) if b < a)
        steps = max(1, ups + downs)
        monotone_ratio = max(ups, downs) / steps
        if monotone_ratio >= 0.9 and sign_flips <= 1:
            return (
                f"residual is monotone in x — try a composite-in-argument like "
                f"y = a*{best.name}(b*x) + c; --affine cannot fit scale-x"
            )

    return None


def fit_composite2(
    xs: list[complex],
    ys: list[complex],
    tolerance: float = 1e-6,
    candidates: Iterable[str] | None = None,
) -> list[CompositeFit]:
    """Rank depth-2 composites y ≈ w(v(x)) for unary primitives w, v.

    Enumerates the cartesian product of unary candidates (~10×10 = 100 pairs).
    A pair is disqualified if any sample raises a domain error in either layer.
    Ranked by ascending max |residual|.
    """
    if len(xs) != len(ys):
        raise FitError(f"xs/ys length mismatch: {len(xs)} vs {len(ys)}")
    if not xs:
        raise FitError("empty dataset")

    names = tuple(candidates) if candidates is not None else _UNARY_CANDIDATES
    n = len(xs)
    y_mean = sum(ys) / n
    ss_tot = sum(abs(y - y_mean) ** 2 for y in ys) or float("inf")

    results: list[CompositeFit] = []
    for outer in names:
        if outer not in NAMED_CLAIMS or is_binary(outer):
            continue
        w = NAMED_CLAIMS[outer]
        for inner in names:
            if inner not in NAMED_CLAIMS or is_binary(inner):
                continue
            v = NAMED_CLAIMS[inner]
            residuals: list[float] = []
            ss_res = 0.0
            n_errors = 0
            for x, y in zip(xs, ys):
                try:
                    pred = w(v(x, complex(0)), complex(0))
                    r = abs(y - pred)
                    residuals.append(r)
                    ss_res += r * r
                except (ZeroDivisionError, ValueError, OverflowError):
                    n_errors += 1
                    residuals.append(float("inf"))
                    ss_res = float("inf")
            max_r = max(residuals) if residuals else float("inf")
            if n_errors < n:
                mean_r = sum(r for r in residuals if r != float("inf")) / max(1, n - n_errors)
            else:
                mean_r = float("inf")
            r2 = (
                1.0 - ss_res / ss_tot
                if ss_tot != float("inf") and ss_res != float("inf")
                else float("-inf")
            )
            results.append(CompositeFit(
                outer=outer, inner=inner,
                max_abs_residual=max_r,
                mean_abs_residual=mean_r,
                r_squared=r2,
                verified=max_r <= tolerance,
                n_samples=n, n_errors=n_errors,
            ))
    results.sort(key=lambda r: (r.max_abs_residual, -r.r_squared))
    return results
