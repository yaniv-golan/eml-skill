# eml_core test-coverage report — 2026-04-19

## Summary

- Command: `PYTHONPATH=skills/_shared python3 -m coverage run -m pytest skills/_shared/eml_core/tests/ -q`
- Test result: **369 passed, 11 skipped** in 7.58s (slow tests gated by `EML_SLOW=1` not exercised).
- Coverage tool: `coverage.py 7.11.3` (C extension).
- **Overall coverage: 90%** — 4197 statements, 429 missed (package + tests), or **89% on the package proper** (excluding the `tests/` subtree).

## Per-module coverage (package only)

| module | stmts | miss | % | notable unexecuted lines |
|---|---:|---:|---:|---|
| `__init__.py`        |   3 |   0 | 100% | — |
| `branch.py`          |  32 |   0 | 100% | — |
| `witnesses.py`       |  51 |   0 | 100% | — |
| `domain.py`          |  59 |   1 |  98% | 241 (negative-count guard) |
| `reference.py`       |  19 |   1 |  95% | 81 |
| `viz.py`             |  70 |   5 |  93% | 114-126 (render-to-file error path) |
| `eml.py`             | 129 |  12 |  91% | 29, 57, 64, 75, 83, 88, 93, 105, 128, 133, 137, 208 (parse-error / token-error branches) |
| `extended.py`        |  35 |   3 |  91% | 108-110 |
| `beam.py`            | 297 |  29 |  90% | 78, 80, 97, 127, 147, 158, 198, 229, 234, 239-240, 261, 268, 286-287, 291, 302, 319-320, 386, 389-390, 403-404, 422, 436, 440-441, 469 (time-budget break, per-level cap block, retain_k snapshot, goal-hash protected-keep bookkeeping, unknown-strategy / unknown-claim validation, seeding error paths) |
| `schemas.py`         | 242 |  23 |  90% | 212-216, 226-227, 235-236, 287-289, 341-342, 370-401 (markdown-emitter edge branches) |
| `branch_audit.py`    |  70 |   8 |  89% | 51-52, 82-83, 111-112, 147-148 (per-probe failure return branches) |
| `symbolic.py`        |  90 |  10 |  89% | 36-38, 152-157, 172-178, 191 (sympy ImportError fallback + full-algebraic simplify path) |
| `goal.py`            |  64 |   7 |  89% | 47, 49, 66, 68, 89, 103, 122 |
| `optimize.py`        |  98 |  12 |  88% | 40-41, 64, 87-88, 100-101, 190-191, 194-199 (peephole-swap error + large-diff abort) |
| `fit.py`             | 302 |  41 |  86% | 117, 131, 141, 144, 148, 158, 182, 193, 239, 241, 250, 261-264, 316, 318, 332, 368-369, 394, 443, 450-451, 455, 461, 489-503, 519, 521, 531, 535, 554 (hint text for monotone/periodic residuals; empty-dataset guards in `fit_composite2`) |
| `identity.py`        | 286 |  49 |  83% | 129-137, 175, 212-214, 219, 238, 323-324, 333, 344-345, 369-372, 405-406, 413-426, 466-504 (sympy-evaluator fallback, domain-pick unreachable branches, report finalizer error paths) |
| `compile.py`         | 294 |  59 |  80% | 91, 216, 234, 239, 254, 258, 263, 266, 271, 277, 283-288 (`log(y, base)` two-arg path), 291, 302, 315, 317-328 (primitive-without-tree diagnostic), 334, 340, 343, 367, 374-378, 383, 391-401, 420, 423, 434-444, 453, 456, 460, 463, 476, 481 |
| **`minimality.py`**  | **212** | **100** | **53%** | 59, 100-115 (`enumerate_trees` binary=False branch + the `K_b<1` skip), 127, 158, 213, 218-219, 225, **282-362** (entire `_audit_minimality_constant` path), 372-378 (`_reconstruct_constant_tree`), 410-411, 413 |

Test-file lines flagged as missed are uninteresting fixture/helper branches; omitted here.

## Gaps narrative

### Severe gap: `minimality.py` at 53%

The entire **constant-target fast path** (`_audit_minimality_constant`, lines 282-362, plus its tree-reconstruction helper `_reconstruct_constant_tree`, lines 371-378) is never entered by the test suite. This is the scalar-complex audit used for arity-0 targets where the leaf alphabet collapses to `("1",)` — the path that makes the pi/gamma-style minimality proofs tractable at large K. `test_minimality.py` and `test_minimality_perf.py` exercise only the generic `_audit_minimality_generic` path (binary=True, leaves `("1","x","y")`). The fallback `enumerate_trees(binary=False)` branch is also dead (line 108's `K_b<1` guard, lines 104-106 n-ary leaf iteration). This is the single largest blind spot in the package.

### Moderate gap: `compile.py` at 80%

Uncovered regions cluster around the **sympy two-arg `log(y, base)`** lowering (lines 283-288) and the **"primitive has no library tree"** diagnostic branch that emits `NeedsTreeEntry` (lines 317-328). The tail (434-481) covers the pretty-printer / JSON-emitter branches for compile diagnostics that are never exercised by `test_compile.py`. Many short single-line misses (91, 216, 234, 239, 254, 258, 263, 266, 271, 277) are `None`-propagation guards in `_lower` — trivial defensive returns, low priority.

### Moderate gap: `identity.py` at 83%

The sympy-evaluator adapter (`_make_sympy_evaluator`, 402-426) and the domain-pick / report-finalizer tails (413-504) are untested. `test_identity.py` never forces the sympy import path or triggers the cross-domain downgrade logic. The `free_symbols` guard (411), the `lambdify` exception branch (414-415), and the numeric-coercion branch (420-422) have zero coverage.

### Parser / evaluator branches in `eml.py`

Every uncovered line (29, 57, 64, 75, 83, 88, 93, 105, 128, 133, 137, 208) is a `ParseError`/`TokenError`/unknown-symbol guard. The parser's happy path is fully exercised; none of the 12 malformed-input rejections are asserted. These are cheap to test (one-line `pytest.raises` each) and would lift `eml.py` to 100%.

### Beam-search pruning corners

`beam.py` is 90% covered but the **time-budget break points inside the product loop** (lines 389-390, 413-414, 415-416, 440-441), the **`retain_k` snapshot hook** (422-425), and the **unknown-strategy / unknown-claim validation** branches (229, 234) are never taken. The per-level-cap protected-kept bookkeeping (302, 403-404) has similarly zero test coverage. These are the branches most likely to regress silently under budget tuning.

### `branch_audit.py` probe failure returns

Each of the four per-probe exception-handling pairs (51-52, 82-83, 111-112, 147-148) is an early-return when a probe fails to evaluate; none are exercised. Matters because the whole point of this module is to surface probe failures in the audit report.

## Top 3 recommended new tests

1. **`test_minimality_constant_fast_path`** — call `audit_minimality` with `leaves=("1",)`, `target_vec=(complex(math.pi),)` (or any easy constant), small `max_k=5`, `track_parents=True`, asserting (a) the result matches the generic path on a constant target where both are legal, and (b) `match_tree` reconstructs via `_reconstruct_constant_tree`. Covers lines 282-362 and 371-378 — the single biggest coverage win (~80 statements).

2. **`test_compile_sympy_two_arg_log_and_missing_witness`** — two assertions: (a) `sympy.log(y, x)` lowers to a `log_x_y` witness instantiation (covers lines 280-288); (b) a `sympy.Function("not_a_witness")(x)` expression triggers the `NeedsTreeEntry` diagnostic branch (covers 317-328). Closes the sympy-compile blind spot.

3. **`test_eml_parser_rejects_malformed_inputs`** — parametrized `pytest.raises(ParseError)` over a dozen malformed strings (unbalanced parens, unknown leaf, arity mismatch, empty string, trailing tokens, etc.) targeting each of `eml.py`'s error-branch lines 29/57/64/75/83/88/93/105/128/133/137/208. Lifts `eml.py` to 100% and locks in parser-hardening invariants cheaply.

## Methodology notes

- Coverage collected only over the `eml_core/` tree via `--include`; the CLI scripts under each `skills/<name>/scripts/*.py` are exercised indirectly by `test_*_cli.py` subprocess invocations, so their direct coverage is not reported here.
- `EML_SLOW=1` was **not** set, so the beam-measurement slow test and the 11 skipped tests (including domain-specific branch-cut probes) are excluded from the run. Running under `EML_SLOW=1` would likely lift `beam.py` slightly but would not change the `minimality.py` finding.
- The `.coverage` sqlite artifact produced by the run is deleted before commit per the task brief.
