# Specialized unary primitives harvest — 2026-04-19

## Motivation

arXiv:2603.21852 Table 4 lists five specialized unary operators alongside the
general-form primitives, each with a **direct-search K** strictly shorter than
the paper's own **compiler K**:

| primitive | compiler K | direct-search K | identity |
|-----------|-----------:|----------------:|----------|
| `x²`      | 75         | **17**          | `mult(x, x)` |
| `x + 1`   | 27         | **19**          | `add(x, 1)` |
| `x − 1`   | 43         | **11**          | `sub(x, 1)` |
| `2x`      | 131        | **19**          | `add(x, x)` |
| `x / 2`   | 131        | **27**          | `div(x, 2)` |

The direct-search values are strictly below the naive "instantiate the general
operator with a constant" cost. This harvest adds the first four to our library
at paper-direct K; `half` is shipped at a K=43 upper bound (the paper's K=27
was not reachable by beam search within a 90-second budget).

## Composition-cost formula

For a unary witness built by substituting concrete subtrees `a`, `b` into the
x/y leaves of a binary witness:

```
K(op(a, b)) = K(op) + n_a · (K(a) − 1) + n_b · (K(b) − 1)
```

where `n_a`, `n_b` are the leaf counts of `x`/`y` in the op's witness tree.
For the `add` / `mult` witnesses both `n_a = n_b = 1`. The "−1" accounts for
each substituted subtree replacing a single-token leaf.

## Per-primitive

### `sq` — K=17 (matches paper direct K=17)

`sq(x) = mult(x, x)`. Substitute `y → x` in the K=17 mult witness.

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1)
```

- K=17 (matches paper direct K exactly)
- depth 8
- Equivalence `max_diff < 1e-14` on `complex-box` (inherits mult's clean domain)

Comparison to general form: using the proven-minimal K=17 mult witness with
both slots filled by `x` leaves (K=1), total = 17 + 1·0 + 1·0 = 17. No savings
over `mult(x, x)` structurally; the specialized entry just pre-compiles it.

### `succ` — K=19 (matches paper direct K=19)

`succ(x) = add(x, 1)`. Substitute `y → 1` in the K=19 add witness.

```
eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(1, 1)), 1))
```

- K=19 (matches paper direct K exactly)
- depth 8
- Equivalence `max_diff < 1e-15` on `real-interval`
- Inherits add's branch-cut limitation — fails on general complex inputs (see
  `add` witness note). Domain is the reference function's natural one, not the
  operator's pure one.

Comparison: 19 + 1·(1−1) + 1·(1−1) = 19. Identical K to composing on the fly,
just pre-compiled.

### `pred` — K=11 (matches paper direct K=11)

`pred(x) = sub(x, 1)`. Substitute `y → 1` in the K=11 sub witness.

```
eml(eml(1, eml(eml(1, x), 1)), eml(1, 1))
```

- K=11 (matches paper direct K exactly)
- depth 4
- Equivalence `max_diff < 1e-15` on `complex-box` — cleaner than `succ` because
  sub is built from `ln` and `exp` only, not add.

Comparison: 11 + 1·0 + 1·0 = 11.

### `double` — K=19 (matches paper direct K=19)

`double(x) = add(x, x)`. Substitute `y → x` in the K=19 add witness.

```
eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(x, 1)), 1))
```

- K=19 (matches paper direct K exactly)
- depth 8
- Equivalence `max_diff < 1e-15` on `real-interval`; same `add` branch-cut
  caveat as `succ`.

Comparison: 19 + 1·0 + 1·0 = 19.

### `half` — K=43 (paper direct K=27 not reached)

Shortest construction found: `exp(sub(ln(x), ln(2)))` where `2 = add(1, 1)`.

```
eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1))), 1)), 1)), 1)
```

- K=43 (paper direct K=27 is 16 tokens shorter than our best)
- depth 14
- Equivalence `max_diff < 1e-14` on `right-half-plane` and `complex-box`;
  identity holds on negative real x because the `ln(x)` branch cut is
  cancelled by the outer `exp`.

Alternative constructions considered:
- `div(x, add(1, 1))`: K = 33 + 1·0 + 1·18 = **51**
- `mult(x, inv(add(1, 1)))`: K = 17 + 0 + (17 + 18 − 1) = **51**
- `exp(sub(ln(x), ln(2)))`: K = **43** ✓ (ships)

Beam search (iter-5 `--seed-witnesses`, `--max-k 27`, `--per-level-cap
100000`, right-half-plane, 90-second time budget) enumerated 467,156
candidates without reaching K=27 or finding any match at K ≤ 27. The paper's
K=27 is presumably a specialized direct-search construction that doesn't
emerge from our library-composition search space.

## Why these belong in the library

1. **Compiler routing.** Every expression `x**2` / `x+1` / `x-1` / `2*x` /
   `x/2` in `/eml-lab compile` can now resolve to a specialized witness rather
   than re-composing the general form on every call. (Dispatch wiring in
   `compile.py` deferred — see "Follow-up" below.)
2. **Paper parity.** Four of the five primitives match paper Table 4 direct-K
   values; these are test anchors for future minimality work.
3. **Leaderboard visibility.** The new rows document that `half` sits at K=43
   vs paper K=27, creating a discoverable open research target.

## Tests

Added to `eml-skill/skills/_shared/eml_core/tests/test_witnesses.py`:

- `SPECIALIZED_UNARY` parametrized fixture covering all five primitives
- `test_specialized_unary_K_and_equivalence` — K match + equivalence_check at
  `tolerance=1e-10`, 512 samples per domain
- `test_specialized_unary_are_arity_one` — pin `arity=1`
- `test_specialized_unary_paper_k_cited` — pin `paper_k` matches paper Table 4
  direct-search value
- `_APPEND_ONLY_SNAPSHOT` extended with K pins for the 5 new entries

Full suite: 262 passed → 269 passed (+7), 8 skipped unchanged.

## Follow-up

- Compile-pipeline routing (`compile.py`) for sympy `Pow(x, 2)`, `Add(x, 1)`,
  `Mul(2, x)`, `Mul(x, Rational(1, 2))` forms so `/eml-lab compile-formula
  "x**2"` prefers the specialized witness. Deferred because sympy normalizes
  these forms in ways that require pattern-matching rather than local_dict
  insertion.
- Beam search for `half` at K ≤ 27 with longer time budget and
  `--seed-subtrees` to exercise structural seeds inside the exp/sub/ln chain.
- Exhaustive minimality for `sq` at K=15 and `pred` at K=9 to promote
  `minimal=True` / `verdict="minimal"` where warranted.

## References

- Paper: arXiv:2603.21852 Table 4, "direct search" column.
- Witness source: `eml-skill/skills/_shared/eml_core/witnesses.py` (append-only block).
- Reference callables: `eml-skill/skills/_shared/eml_core/reference.py` (`NAMED_CLAIMS`).
- Tests: `eml-skill/skills/_shared/eml_core/tests/test_witnesses.py`.
- Leaderboard: `docs/leaderboard.md`.
