"""Fit module: library-first regression."""

from __future__ import annotations

import cmath
import csv
from pathlib import Path

import pytest

import random

from eml_core.fit import (
    FitError,
    diagnose_affine_hint,
    fit_affine,
    fit_binary,
    fit_composite2,
    fit_unary,
    load_csv,
    load_xy_csv,
)


def _write_csv(path: Path, rows: list[tuple]) -> None:
    with path.open("w") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)


def test_load_xy_csv_with_header(tmp_path: Path) -> None:
    p = tmp_path / "h.csv"
    _write_csv(p, [("x", "y"), (1.0, 2.0), (3.0, 4.0)])
    xs, ys = load_xy_csv(p)
    assert list(xs) == [1.0 + 0j, 3.0 + 0j]
    assert list(ys) == [2.0 + 0j, 4.0 + 0j]


def test_load_xy_csv_no_header(tmp_path: Path) -> None:
    p = tmp_path / "n.csv"
    _write_csv(p, [(1.0, 2.0), (3.0, 4.0)])
    xs, ys = load_xy_csv(p)
    assert list(xs) == [1.0 + 0j, 3.0 + 0j]
    assert list(ys) == [2.0 + 0j, 4.0 + 0j]


def test_load_xy_csv_empty_raises(tmp_path: Path) -> None:
    p = tmp_path / "e.csv"
    p.write_text("")
    with pytest.raises(FitError):
        load_xy_csv(p)


def test_load_csv_three_column(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    _write_csv(p, [("x", "y", "z"), (1, 2, 3), (4, 5, 9)])
    cols = load_csv(p)
    assert len(cols) == 3
    assert cols[0] == [1 + 0j, 4 + 0j]
    assert cols[2] == [3 + 0j, 9 + 0j]


def test_fit_recovers_ln() -> None:
    xs = [complex(x, 0) for x in (0.5, 1.0, 1.5, 2.0, 3.0, 5.0)]
    ys = [cmath.log(x) for x in xs]
    results = fit_unary(xs, ys, tolerance=1e-9)
    assert results[0].name == "ln"
    assert results[0].verified is True
    assert results[0].max_abs_residual < 1e-12


def test_fit_recovers_sqrt_over_sin() -> None:
    xs = [complex(x, 0) for x in (0.25, 1.0, 4.0, 9.0, 16.0, 25.0)]
    ys = [cmath.sqrt(x) for x in xs]
    results = fit_unary(xs, ys)
    assert results[0].name == "sqrt"
    assert results[0].verified is True


def test_fit_no_match_for_x_cubed() -> None:
    xs = [complex(x, 0) for x in (1, 2, 3, 4, 5, 10)]
    ys = [x**3 for x in xs]
    results = fit_unary(xs, ys, tolerance=1e-6)
    assert not any(r.verified for r in results)
    assert results[0].max_abs_residual > 1e-6


def test_fit_handles_evaluation_errors() -> None:
    xs = [complex(x, 0) for x in (0.0, 1.0, 2.0)]
    ys = [complex(0, 0), complex(0, 0), cmath.log(2)]
    results = fit_unary(xs, ys)
    ln_result = next(r for r in results if r.name == "ln")
    assert ln_result.n_errors == 1


def test_fit_empty_raises() -> None:
    with pytest.raises(FitError):
        fit_unary([], [])


def test_fit_binary_recovers_mult() -> None:
    xs = [complex(x, 0) for x in (1, 2, 3, 4)]
    ys = [complex(y, 0) for y in (5, 7, 11, 2)]
    zs = [x * y for x, y in zip(xs, ys)]
    results = fit_binary(xs, ys, zs, tolerance=1e-9)
    assert results[0].name == "mult"
    assert results[0].verified is True
    assert results[0].max_abs_residual < 1e-12


def test_fit_binary_recovers_pow() -> None:
    xs = [complex(x, 0) for x in (2, 3, 4, 5)]
    ys = [complex(y, 0) for y in (0.5, 2, 3, 1.5)]
    zs = [cmath.exp(y * cmath.log(x)) for x, y in zip(xs, ys)]
    results = fit_binary(xs, ys, zs, tolerance=1e-9)
    assert results[0].name == "pow"
    assert results[0].verified is True


def test_fit_affine_snaps_pi() -> None:
    # y = pi * sin(x)
    xs = [complex(x, 0) for x in (0.3, 0.7, 1.1, 1.5, 1.9, 2.3)]
    ys = [cmath.pi * cmath.sin(x) for x in xs]
    results = fit_affine(xs, ys, tolerance=1e-9, snap_tol=1e-6)
    assert results[0].name == "sin"
    assert results[0].verified is True
    assert results[0].a_snapped == "pi"
    assert results[0].b_snapped == "0"


def test_fit_affine_snaps_log_change_of_base() -> None:
    # y = (1/ln(10)) * ln(x) = log10(x)
    # The affine fit on 'ln' should snap a to 1/ln(10), b to 0.
    xs = [complex(x, 0) for x in (2, 3, 5, 7, 11, 100)]
    ys = [cmath.log10(x) for x in xs]
    results = fit_affine(xs, ys, tolerance=1e-9, snap_tol=1e-6)
    # ln should verify with a = 1/ln(10) = 0.4343…
    ln_fit = next(r for r in results if r.name == "ln")
    assert ln_fit.verified is True
    assert ln_fit.a_snapped == "1/ln(10)"


def test_fit_affine_ignores_cubic() -> None:
    xs = [complex(x, 0) for x in (0.5, 1, 1.5, 2, 3, 5)]
    ys = [x**3 for x in xs]
    results = fit_affine(xs, ys, tolerance=1e-6)
    # No unary w(x) affinely fits x^3 within 1e-6
    assert not any(r.verified for r in results)


def test_fit_affine_snaps_catalan() -> None:
    # y = G * sin(x), where G is Catalan's constant ≈ 0.9159656
    catalan = 0.9159655941772190
    xs = [complex(x, 0) for x in (0.3, 0.7, 1.1, 1.5, 1.9, 2.3, 2.7)]
    ys = [catalan * cmath.sin(x) for x in xs]
    results = fit_affine(xs, ys, tolerance=1e-9, snap_tol=1e-9)
    sin_fit = next(r for r in results if r.name == "sin")
    assert sin_fit.verified is True
    assert sin_fit.a_snapped == "G_catalan"
    assert sin_fit.b_snapped == "0"


def test_fit_affine_snaps_log2_e() -> None:
    # y = log2(x) = (1/ln(2)) * ln(x); 1/ln(2) == log2(e) ≈ 1.4426950
    xs = [complex(x, 0) for x in (2, 3, 5, 8, 16, 100)]
    ys = [cmath.log(x) / cmath.log(2) for x in xs]
    results = fit_affine(xs, ys, tolerance=1e-9, snap_tol=1e-9)
    ln_fit = next(r for r in results if r.name == "ln")
    assert ln_fit.verified is True
    assert ln_fit.a_snapped == "log2(e)"


def test_fit_affine_noise_robust_snap() -> None:
    # y = pi * sin(x) + N(0, sigma); skill should still snap pi when given sigma.
    rng = random.Random(42)
    sigma = 0.01
    xs = [complex(0.1 * k + 0.05, 0) for k in range(60)]
    ys = [cmath.pi * cmath.sin(x) + complex(rng.gauss(0, sigma), 0) for x in xs]

    # Without noise_sigma the fit fails to verify and likely won't snap.
    bare = fit_affine(xs, ys, tolerance=1e-9, snap_tol=1e-9)
    sin_bare = next(r for r in bare if r.name == "sin")
    assert sin_bare.verified is False  # 1e-9 tolerance is unreachable under sigma=0.01

    # With noise_sigma, tolerance and snap_tol auto-loosen; pi snaps.
    noisy = fit_affine(xs, ys, tolerance=1e-9, snap_tol=1e-9, noise_sigma=sigma)
    sin_fit = next(r for r in noisy if r.name == "sin")
    assert sin_fit.verified is True
    assert sin_fit.a_snapped == "pi"
    # Standard errors are populated and finite.
    assert sin_fit.se_a is not None
    assert sin_fit.se_b is not None
    assert sin_fit.se_a > 0


def test_fit_composite2_recovers_sin_of_ln() -> None:
    # y = sin(ln(x)) for x > 0
    xs = [complex(x, 0) for x in (0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0)]
    ys = [cmath.sin(cmath.log(x)) for x in xs]
    results = fit_composite2(xs, ys, tolerance=1e-9)
    assert results[0].outer == "sin"
    assert results[0].inner == "ln"
    assert results[0].verified is True
    assert results[0].max_abs_residual < 1e-12


def test_fit_composite2_no_match_for_x_cubed() -> None:
    xs = [complex(x, 0) for x in (1, 2, 3, 4, 5)]
    ys = [x**3 for x in xs]
    results = fit_composite2(xs, ys, tolerance=1e-6)
    assert not any(r.verified for r in results)


def test_fit_affine_hint_scale_x_sin() -> None:
    # y = 2 * sin(3*x) is outside the affine family (scale-x inside sin).
    # --affine cannot fit this; the residual of the best sin affine candidate
    # should oscillate (many sign flips) → hint suggests scale-x composite.
    import math
    xs = [complex(2 * math.pi * k / 99, 0) for k in range(100)]
    ys = [complex(2.0 * math.sin(3.0 * x.real), 0) for x in xs]
    results = fit_affine(xs, ys, tolerance=1e-6)
    # Sanity: affine cannot verify this dataset.
    assert not any(r.verified for r in results)
    hint = diagnose_affine_hint(xs, ys, results)
    assert hint is not None
    assert "scale-x" in hint
    assert "periodicity" in hint


def test_fit_affine_hint_absent_when_fit_verifies() -> None:
    # y = pi * sin(x) is affinely fit by sin; no hint should fire.
    xs = [complex(x, 0) for x in (0.3, 0.7, 1.1, 1.5, 1.9, 2.3)]
    ys = [cmath.pi * cmath.sin(x) for x in xs]
    results = fit_affine(xs, ys, tolerance=1e-9, snap_tol=1e-6)
    assert any(r.verified for r in results)
    assert diagnose_affine_hint(xs, ys, results) is None
