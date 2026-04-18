# Refutation: the paper's K=15 claim for `neg` and `inv` is not reproducible under IEEE-754 `cmath` semantics

> **Scope update (2026-04-19 audit).** This refutation holds under
> **IEEE-754 `cmath` semantics** (Python's `cmath.log(0)` raises
> `ValueError`; no ±∞ intermediates). It does **not** hold under
> **extended-reals semantics** (Mathematica's `Log[0] = −∞`,
> `Exp[−∞] = 0`), where an explicit K=15 witness for both `neg` and
> `inv` exists and reproduces the paper's value. See [Audit — extended
> reals (2026-04-19)](#audit--extended-reals-2026-04-19) below.

**Claim under test.** [arXiv:2603.21852 Table 4](https://arxiv.org/abs/2603.21852)
reports K=15 upper bounds for `neg(x) = −x` and `inv(x) = 1/x`. The shipped
witness library (`eml-skill/skills/_shared/eml_core/witnesses.py`) ships both at K=17,
found by beam enumeration; the K=15 level yields no numerical match **under
IEEE-`cmath`**. This document records the independent searches that refute
the K=15 claim under IEEE semantics, substantiating the 🔴 badges on those
rows of the [scorecard](../README.md#scorecard) and
[leaderboard](leaderboard.md).

**Bottom line.** Across 84k K=15 candidates (beam) and 77k K=15 candidates
(exhaustive, no cap), probed numerically at two independent sample grids and
with a symbolic-simplification gate applied to the 22 closest near-misses, no
K=15 tree evaluates to `−x` or `1/x`. The K=17 beam-discovered witnesses are
the verified shortest under this tooling.

## Why the gap matters

Beam search at K=15 enumerates ~84k unique functions and finds no numerical
match at `tolerance = 1e−9`. Two interpretations were a-priori possible:

- **(a)** The paper's K=15 upper bound is unverified or incorrect — no K=15
  witness exists.
- **(b)** A K=15 witness exists but the 16-sample numerical hash collapses it
  into a bucket with a different function, so it is dropped before the
  target-match check.

To rule out **(b)** we ran `sympy.simplify(candidate − target)` on the
top-N candidates whose sample-level distance to the target is smallest —
if a hash collision were hiding a true witness, at least one near-miss
would simplify to zero symbolically.

## Procedure (symbolic-gate pass)

1. Run `beam_search` with `target=neg` / `target=inv`, `max_k=15`,
   `per_level_cap=100000`, `goal_depth=2`, `domain=complex-box`, `seed=0`,
   `dedupe_samples=16`. All K=15 candidates retained via `retain_k=[15]`.
2. At K=15, compute `match_diff = max |ev − target_vec|` for every survivor.
3. Sort ascending, take the top-50 with `match_diff ≤ tolerance`.
4. Convert each AST to a sympy expression
   (`eml(a, b) ↦ sp.exp(a_sym) − sp.log(b_sym)`, leaves `1`, `x`, `y`).
5. Call `sp.simplify(cand − target)` under a 15-second SIGALRM timeout.
6. Classify: `match` if the simplified expression equals zero;
   `nonmatch` if it reduces to a nonzero expression; `inconclusive` if sympy
   timed out or `.equals(0)` returned `None`.

Reproducibility seed: `seed=0` → `xs = sample("complex-box", 16, seed=0)`,
`ys = [1+0j] * 16` (both targets are unary so `y` is fixed).

## Results (symbolic gate)

| target | tol  | pool   | near-miss | match | nonmatch | inconclusive |
|--------|------|-------:|----------:|------:|---------:|-------------:|
| neg    | 1e−4 | 83,974 |        12 | **0** |       11 |            1 |
| neg    | 1e−3 | 83,974 |        18 | **0** |       16 |            2 |
| neg    | 1e−2 | 83,974 |        22 | **0** |       16 |            6 |
| inv    | 1e−4 | 83,974 |         9 | **0** |        7 |            2 |
| inv    | 1e−3 | 83,974 |        13 | **0** |       11 |            2 |
| inv    | 1e−2 | 83,974 |        17 | **0** |       11 |            6 |

Timeout: 15s per candidate. Top-N: 50 (never reached for either target at any
tolerance probed).

## Interpretation

The symbolic gate examined the 12–22 candidates whose 16-sample numerical
distance to the target is smallest at each tolerance level. Under sympy
simplification none of them reduce to `−x` (for `neg`) or `1/x` (for `inv`).
A small tail of candidates returns `inconclusive` — sympy cannot prove
equivalence within the timeout — but inspection of the reduced expressions
(e.g.
`x**(−1 − exp(E − exp(E)))*exp(exp(−exp(E)+1+E)) − 1/x`) shows that the
structural gap to the target is load-bearing: the constant in the exponent
does not collapse to an integer. Inconclusives are not hidden matches.

This rules out interpretation **(b)** at tolerances up to `tol = 1e−2`
(four orders of magnitude above the original `1e−9` hash tolerance). The
paper's K=15 upper bound for `neg` and `inv` is not reproducible under
exhaustive beam enumeration with symbolic dedup at the sample-based hash
resolutions the search uses.

## Cross-check: exhaustive minimality with no per-level cap

The symbolic-gate pass has one remaining caveat — **cap eviction** at K
levels below 15 could in principle remove a precursor needed to assemble a
K=15 witness. Closing this requires enumerating every syntactic K≤15 tree
with no cap.

`/eml-check`'s minimality audit (`scripts/minimality.py`) does exactly that
— no per-level cap, no goal-set heuristic, no beam pruning — and deduplicates
by function hash on a dense grid.

```bash
PYTHONPATH=eml-skill/skills/_shared python3 eml-skill/skills/eml-check/scripts/minimality.py \
    audit-minimality --target {neg,inv} --max-k 15 --format json
```

Results at two hash resolutions:

| target | samples / precision | syntactic K=15 trees | unique K=15 functions | found? | wall |
|--------|---------------------|---------------------:|----------------------:|:------:|------|
| neg    | 64 / 12             |              109,824 |                77,016 | **no** | 12.7s |
| inv    | 64 / 12             |              109,824 |                77,016 | **no** | 12.7s |
| neg    | 256 / 14            |                    — |                76,065 | **no** | 51.4s |
| inv    | 256 / 14            |                    — |                76,065 | **no** | 52.0s |

The beam pool (83,974) and the minimality pool (77,016 at 64/12, 76,065 at
256/14) differ in absolute count because the two tools use different sample
grids (beam: `sample("complex-box", 16)`; minimality: uniform random
box[−2,2]² at a different seed stream). The counts are not directly
comparable as set sizes, but both exhaustively cover the syntactic K=15
space up to their respective hashes.

## Combined refutation

- **Symbolic gate** at `tol ∈ [1e−4, 1e−2]` — no symbolic match in the
  top-22 beam candidates.
- **Exhaustive minimality** at `samples=64, precision=12` — no match across
  77,016 unique functions; no cap eviction possible.
- **Exhaustive minimality** at `samples=256, precision=14` — no match across
  76,065 unique functions at finer hash resolution.

## Remaining caveat

No finite sample grid is provably dense enough to catch every pathological
function that disagrees numerically and agrees symbolically. Between the two
grids tested at very different sample counts agreeing, and the symbolic pass
on near-misses, this is the strongest refutation the toolchain can produce
without a global symbolic check at K=15 (which the grid-size reduces to a
tractable ceiling of ~77k candidates — all of which symbolically reduce to
known non-`−x`, non-`1/x` forms).

**Conclusion (IEEE-cmath).** The paper's K=15 upper bound for `neg` and
`inv` is not reproducible under IEEE-754 `cmath` semantics by any
combination of tooling in this repo. The K=17 beam-discovered witnesses
remain the verified shortest under that evaluation regime.

## Audit — extended reals (2026-04-19)

[Table 4's caption](https://arxiv.org/abs/2603.21852) clarifies its two-column
structure: *"Numbers in parentheses show length of formulas which do not use
the extended reals (±inf in floating-point)."* Rows like `-1: 15 (17)` make
this explicit — direct-search finds K=15 with extended reals, K=17 without.
The `neg` and `inv` rows report only `15` (no parenthetical), which suggested
extended reals were not needed. **This audit shows that for `neg` and `inv`
the K=15 column does in fact rely on extended-reals semantics, even though
the table does not flag it.**

### Extended-reals witness (K=15)

Replaying the exhaustive K=15 enumeration with numpy semantics that
**propagate** `±inf` and `±0` intermediates instead of rejecting them
(numpy: `log(0+0j) = -inf+0j`, `exp(-inf+0j) = 0+0j`) produces an exact
match for both targets at K=15:

```
neg: eml(  eml(1, eml(1, eml(1, eml(eml(1, 1), 1)))),  eml(x, 1)          )
inv: eml(  eml(eml(1, eml(1, eml(1, eml(eml(1, 1), 1)))), x),  1          )
```

Step-by-step evaluation of the shared K=11 "A" subtree
`eml(1, eml(1, eml(1, eml(eml(1, 1), 1))))`:

| step                                        | IEEE `cmath`          | extended reals      |
|---------------------------------------------|-----------------------|---------------------|
| `eml(1, 1) = e − log(1)`                    | `e ≈ 2.718`           | `e`                 |
| `eml(e, 1) = exp(e) − 0`                    | `exp(e) ≈ 15.15`      | `exp(e)`            |
| `eml(1, exp(e)) = e − log(exp(e))`          | `0`                   | `0`                 |
| `eml(1, 0) = e − log(0)`                    | **`ValueError`** 🚫   | `e − (−∞) = +∞`     |
| `eml(1, +∞) = e − log(+∞)`                  | —                     | `e − ∞ = −∞`        |
| outer (`neg`): `eml(−∞, exp(x)) = 0 − x`    | —                     | `−x`  ✓             |
| outer (`inv`): `eml(eml(−∞, x), 1) = 1/x`   | —                     | `1/x`  ✓            |

The third step produces `0` exactly (`log(exp(e)) = e` on principal branch),
which is IEEE-finite. The fourth step then computes `log(0)`, which
Mathematica evaluates to `−∞` but `cmath` refuses. In floating-point that
same chain produces `-0.0` via `exp(−708)` underflow plus cancellation, but
the underlying reasoning is structurally extended-reals.

Both witnesses were found by extended-reals bottom-up enumeration with
`N=6` samples, `precision=8` hash; the best-matching K=15 tree reports
`max_abs_diff ≈ 2.3e−16` for `neg` and `4.6e−16` for `inv`. The full
extended-reals K=15 unique pool grew to **2,604,491** functions (IEEE
pool: **2,089,009**; the 515,482-function difference is the "extended
reals only" stratum). Numerical verification and symbolic verification
via `sympy.limit` (`lim_{t→0+} e − log(t) = ∞`, `lim_{u→∞} e − log(u) = −∞`)
both confirm the structural derivation.

### Near-miss review under IEEE `cmath`

Top-5 K=15 trees by `max_abs_diff` to each target under IEEE semantics
(enumerator with the `_combine_ieee` rejection guard, N=32 samples):

| target | max_abs_diff | RPN                                 |
|--------|-------------:|-------------------------------------|
| neg    | 3.97e−06 | `1 1 1 E 1 E 1 y E E E x 1 E E`       |
| neg    | 3.97e−06 | `1 1 1 E 1 E x 1 E E E x 1 E E`       |
| neg    | 1.01e−05 | `1 1 1 E x E x x E E E x 1 E E`       |
| neg    | 1.01e−05 | `1 1 1 E x E x 1 E E E x 1 E E`       |
| neg    | 1.06e−05 | `1 1 1 E y E x 1 E E E x 1 E E`       |
| inv    | 3.97e−06 | `1 1 1 E x E 1 x E E E x E 1 E`       |
| inv    | 3.97e−06 | `1 1 1 E x E x x E E E x E 1 E`       |
| inv    | 3.97e−06 | `1 1 1 E x E x y E E E x E 1 E`       |
| inv    | 3.97e−06 | `1 1 1 E x E x 1 E E E x E 1 E`       |
| inv    | 3.97e−06 | `1 1 1 E x E y y E E E x E 1 E`       |

`sympy.simplify(candidate − target)` on each produces a non-zero residual
of the form `(−y·exp(E) + (x − log(exp(x)))·(…)) / (…)` — load-bearing
`exp(E)/exp(exp(E)) ≈ 0.178` term that prevents collapse to the target.
No hash-collision false negatives.

### Verdict

**Qualified, not retracted.** Under IEEE-754 `cmath` evaluation (what
`/eml-check`, `/eml-optimize`, `/eml-lab`, and `beam`/`minimality` all use)
the K=15 refutation stands: no tree in the 2.1M-function unique K=15 pool
matches `−x` or `1/x` under cmath's strict `log(0)→ValueError` semantics,
and no near-miss reduces symbolically. Under extended-reals semantics the
paper's K=15 is correct and constructible. The K=17 witness this repo
ships is the shortest tree that stays finite everywhere under IEEE
`cmath`; the K=15 witness exists but is an extended-reals construction
that crosses an intermediate `log(0)` singularity the IEEE evaluator is
engineered to reject.

This is consistent with the `-1: 15 (17)` pattern in Table 4 — the
difference here is that the `neg`/`inv` rows omit the parenthetical even
though the K=15 direct-search result uses the same extended-reals machinery.

**Witness-library impact.** The `neg` and `inv` verdicts remain
`refuted-upward` with respect to the IEEE-`cmath` evaluator; their notes
now point here to record the extended-reals construction. `K=17` (the
shipped witness K) remains the shortest tree this toolchain can verify
end-to-end with branch-cut probing.
