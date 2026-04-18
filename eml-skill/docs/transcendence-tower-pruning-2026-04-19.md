# Transcendence-tower pruning for EML beam search

**Date:** 2026-04-19
**Module:** `skills/_shared/eml_core/tower.py`
**Tests:** `skills/_shared/eml_core/tests/test_tower.py` (21 tests)
**Baseline delta:** 351 → 372 passed, 11 skipped unchanged

## Motivation

Beam search enumerates EML subtrees bottom-up and scores each candidate by
numerical closeness to a target. Many early-stage candidates are numerically
interesting but algebraically incapable of ever reaching the target — e.g.
any subtree evaluating to a purely real, rational number cannot, under any
further combination that stays within the RPN budget, produce `π` (which
needs both `π` and `i` in its minimum tower). We attach a coarse
"signature" to each subtree and prune on provable incompatibility.

## Signature definition

A signature is a `set[str]` drawn from the tag alphabet

```
TAGS = {"x", "y", "e", "pi", "i", "log"}
```

Tags are syntactic and conservative — a tag may be present even when the
underlying value doesn't actually live in that extension (post cancellation
sympy hasn't surfaced). This is on purpose: over-tagging a subtree makes
the subtree look *more* capable, which never prunes it incorrectly.

| tag | meaning                                                             |
|-----|---------------------------------------------------------------------|
| `x` | sympy expression has `x` as a free symbol                           |
| `y` | sympy expression has `y` as a free symbol                           |
| `e` | expression contains `sp.E` or any `exp(q)` with non-zero argument   |
| `pi`| expression contains `sp.pi` (surfaces from `log(-q)` simplification)|
| `i` | expression contains `sp.I`                                          |
| `log`| expression contains `log(q)` with `q ∉ {0, 1}`                     |

Signatures are computed by: convert AST → sympy (same as `symbolic.py`),
light canonicalization (`expand_log`, `expand_power_exp`), then
`sp.preorder_traversal` with per-node tag rules. The result is memoized
on canonical RPN so repeated subtrees across beam calls share one sympy
walk.

## Lindemann–Weierstrass facts relied on

1. **(L1)** For algebraic `α ≠ 0`, `exp(α)` is transcendental.
   In particular, `e = exp(1)` is transcendental over ℚ.
2. **(L2)** For algebraic `α ∉ {0, 1}`, `log(α)` (principal branch) is
   transcendental. Hence `log(2)`, `log(-1) = iπ`, etc.
3. **(L3)** `π` is transcendental (special case via `log(-1)`).

These are classical theorems, no conjectures involved.

## Schanuel-conditional statements NOT used

The predicate is carefully built to avoid needing any of the following
(any prune decision that would require one of these falls through to
"keep"):

- **Algebraic independence of `{π, e}` over ℚ.** Open. Would allow us to
  certify that a subtree with sig `{e}` alone cannot reach `π·e` without
  introducing `π`. We don't try.
- **Algebraic independence of `{log p₁, …, log pₙ}`.** Known via Baker
  but we stay inside L-W; no prune depends on it.
- **Strict subtower claims** of the form "sig A is strictly weaker than
  sig B" beyond simple set subset tests. We only prune on missing tags
  that the remaining RPN budget demonstrably cannot introduce.

## Target signatures

`target_tower_signature(name)` returns the minimum signature for each
`NAMED_CLAIMS` entry via a hand-curated override table. Examples:

| target | signature            |
|--------|----------------------|
| `exp`  | `{x, e}`             |
| `ln`   | `{x, log}`           |
| `sin`  | `{x, e, i}`          |
| `pi`   | `{pi, i}`            |
| `e`    | `{e}`                |
| `neg`  | `{x}`                |
| `sub`  | `{x, y}`             |
| `pow`  | `{x, y, e, log}`     |

A missing target name returns the full tag alphabet, which disables
pruning against that target (the safe default).

## Pruning predicate

```python
can_reach_target(subtree_sig, target_sig, remaining_k) -> bool
```

- Computes `missing = (target_sig − subtree_sig) ∩ {e, pi, i, log}`.
  Free-variable tags (`x`, `y`) are **not** in the introducible set
  because the predicate doesn't try to reason about them — presence
  or absence of `x`/`y` never triggers a prune.
- Each `eml()` node costs ≥3 RPN tokens (two leaves + `"E"`) and,
  conservatively, can introduce **at most one** new algebraic tag.
- Prune iff `remaining_k < 3 · |missing|`.

Returns `True` (keep) otherwise — never false-positive-prune when the
budget math is unclear.

## Prune-ratio estimates (K_max = 9)

Measured by enumerating all structurally distinct EML trees at a given
subtree size and counting how many would be pruned for a given target.

| K_sub | remaining | target | pruned / total | ratio |
|-------|-----------|--------|----------------|-------|
| 5     | 4         | `pi`   | 54 / 54        | 100%  |
| 5     | 4         | `exp`  | 0 / 54         | 0%    |
| 5     | 4         | `sub`  | 0 / 54         | 0%    |
| 5     | 4         | `e`    | 0 / 54         | 0%    |
| 5     | 4         | `sin`  | 0 / 54         | 0%    |
| 7     | 2         | `pi`   | 405 / 405      | 100%  |
| 7     | 2         | `sin`  | 405 / 405      | 100%  |
| 7     | 2         | `exp`  | 3 / 405        | 0.7%  |
| 7     | 2         | `e`    | 3 / 405        | 0.7%  |

Interpretation:

- **Huge win for `pi`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`** —
  targets that require the full `{pi, i}` or `{e, i}` sub-tower. The
  predicate kills entire subtree branches that stay in `ℚ(e)` when the
  budget is tight.
- **Zero win for `exp`, `sub`, `e`** at K=9 — the target sigs are so
  small that most subtrees already cover them. Signature pruning is
  not the right tool here; peephole / goal-propagation already do the
  work.

## Five-line beam.py integration sketch

In the bottom-up candidate expansion loop, given a freshly built
candidate `cand`, the beam's known `target_name`, and its max budget
`K_cap`:

```python
from .tower import can_reach_target, subtree_signature, target_tower_signature

_tsig = target_tower_signature(target_name)  # hoist: precompute once per beam run
# … inside the candidate-admit loop …
if not can_reach_target(subtree_signature(cand), _tsig, K_cap - k_tokens(cand)):
    continue  # algebraically incapable; skip without adding to pool
```

Placement: call `can_reach_target` **after** the structural filters (leaf
check, K limit) but **before** the expensive ev-vector / scoring pass.
Pool insertion stays unchanged.

## Limitations and follow-ups

- The "≤1 new tag per eml" budget bound is deliberately loose; a
  sharper analysis could halve the 3-token cost in some cases.
- Targets with signature = full TAGS (unknown/unmapped) get no pruning.
  Extending `_TARGET_SIG_OVERRIDES` when adding new `NAMED_CLAIMS`
  entries is a free win.
- Signature computation is sympy-bound and slower than pure numeric
  scoring. The RPN-keyed LRU cache amortizes this across beam levels —
  but a deep beam may need a bounded-depth fallback.
