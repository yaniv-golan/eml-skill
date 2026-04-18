# `shape-search` — top-down constant-first driver

Companion to `scripts/optimize.py search` (bottom-up beam). Where beam
combines subtrees K-by-K and runs into memory at large K, `shape-search`
enumerates **whole-tree shapes** at fixed K, prunes leaf labelings by
numerical constant-feasibility, and evaluates survivors in mpmath against
a target constant. The two strategies are orthogonal:

| | beam | shape-search |
|---|---|---|
| Direction | bottom-up | top-down |
| State | dedupe hash per K | none (stateless per shape) |
| Bottleneck | memory (per-level cap) | time (shape × labeling product) |
| Target type | any claim | **arity-0 constants only** |
| Pruning | goal propagation + hash dedupe | numerical x,y-independence filter |

## Location

- Driver: `skills/eml-optimize/scripts/shape_search.py`
- Core: `skills/_shared/eml_core/shape_feasibility.py` (shape enumeration,
  feasibility probe — shipped 2026-04-19)
- Tests: `skills/_shared/eml_core/tests/test_shape_search_cli.py`

## Usage

```bash
# Find e — expected at K=3 (`1 1 E`)
PYTHONPATH=skills/_shared python3 \
  skills/eml-optimize/scripts/shape_search.py \
  --target e --max-k 3

# Find zero — expected at K=7 via the exp(x)-log(exp(exp(x)))=0 family
PYTHONPATH=skills/_shared python3 \
  skills/eml-optimize/scripts/shape_search.py \
  --target zero --max-k 7

# Null on pi — no short witness exists; times out gracefully
PYTHONPATH=skills/_shared python3 \
  skills/eml-optimize/scripts/shape_search.py \
  --target pi --max-k 13 --time-budget 600
```

## Flags

| flag | default | purpose |
|------|---------|---------|
| `--target` | *(req)* | `pi`, `e`, `i`, `zero`, `minus_one`, `two`, `half_const` |
| `--max-k` | 9 | odd ceiling on K (RPN token count) |
| `--time-budget` | 600 | wall-clock seconds |
| `--precision` | 40 | mpmath decimal digits for value compare |
| `--tolerance` | 1e-30 | `|value - reference|` match threshold |
| `--format` | markdown | `markdown` or `json` |

## Algorithm

1. For `K` in `1, 3, 5, ..., max_k`:
2. Enumerate all binary-tree shapes with `(K+1)/2` leaves — Catalan count
   grows as `1, 1, 2, 5, 14, 42, 132, 429, ...` for K=1..15.
3. For each shape, iterate leaf labelings in `{1, x, y}^leaves` filtered by
   `shape_feasibility.feasible_labelings(target_is_constant=True)` — the
   probe samples at 6 independent (x,y) pairs and keeps only labelings that
   evaluate to the same complex value within `1e-8` at every sample.
4. Compile survivor to RPN, evaluate in mpmath at `--precision` digits on
   `(x=1, y=1)` (any point works — tree is numerically constant).
5. Report match if `|value - reference| < --tolerance`.

## Why constant-only

`feasible_labelings` only prunes when the target is a constant. For a
non-constant target (e.g. `sin`) every labeling is feasible (any
variable-dependent expression might be the target), so the driver has no
pruning leverage and degenerates to naive enumeration. Non-constant targets
are handled better by beam's bottom-up hashing.

## Observed pruning power (from `docs/shape-feasibility-2026-04-19.md`)

At K=9 (5 leaves, 243 labelings per shape, 14 shapes = 3,402 total):
feasibility keeps **24** (99.3% pruned). At K=11 (6 leaves, 729 per shape,
42 shapes = 30,618 total): keeps **127** (99.6% pruned).

## Complement to beam — when to use which

- **beam with `--target exp`, `--max-k 9`**: classic function search;
  stateful bottom-up; hashing finds structure sharing.
- **shape-search with `--target pi`, `--max-k 13`**: no memory ceiling;
  exhaustive within K's shape-labeling product; surfaces constants beam's
  cap evicts.

The K=7 counter-example (`exp(x) - log(exp(exp(x))) = 0`, the witness for
`zero`) illustrates the kind of non-trivial constant a variable-leaf shape
can produce — something an "all-1-leaves = only constants" shortcut would
miss. The shape-search driver's numerical probe catches it; beam finds it
too, but only because the intermediate `exp(x)` at K=3 survives dedupe to
combine later. For constants whose intermediate compositions don't survive
the per-level cap, shape-search is the lever.

## Known limits

- **Shape+labeling explosion.** At K=13 the Catalan count is 132 and
  labelings reach `3^7 = 2187`, giving 288,684 (shape, labeling) pairs
  before feasibility pruning. The feasibility probe cost dominates runtime
  at K≥11. There is no obvious structural improvement short of a full
  sympy gate per survivor.
- **Shape-symmetry overcounting.** The enumerator does not canonicalize
  commutative or associative equivalents — `eml` is neither. Shapes remain
  distinct under its asymmetric semantics (`exp(a) - log(b)`).
- **Feasibility false positives.** Numerical probe could in principle
  accept a labeling that is only constant on 6 sample points but varies at
  the 7th. On EML's operator set we have not observed this. A stricter
  gate could plug in sympy `simplify` at the cost of 100× slowdown per
  labeling.

## Pi: has shape-search closed the K=54..121 gap?

No. Running shape-search for pi at `max-k=11` with 60s budget evaluates
162 survivors, all non-matches. At max-k=13+ runtime blows past a 10-min
budget before completing the shape space. The K=54..121 gap for pi is not
cracked by top-down either — which aligns with the bottom-up beam null
(`docs/pi-k119-beam-null-2026-04-19.md`), the constant-hash null
(`docs/pi-constant-hash-attempt-2026-04-19.md`), and the tower-prune null
(`docs/pi-tower-prune-attempt-2026-04-19.md`). Four independent strategies
now say the same thing: pi's shortest witness in this EML library is
either K=121 (the shipped upper bound) or somewhere in a range that
requires a qualitatively new proof technique, not more CPU.
