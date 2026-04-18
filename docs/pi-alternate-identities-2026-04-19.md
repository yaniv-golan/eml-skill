# `pi` alternate-identity audit — 2026-04-19

Current `pi` witness: **K=137**, tree harvested via the proof-engine 9-stage
pi/i construction (`proof-engine/proofs/eml-pi-and-i-from-1/`). Task framing
referenced K=121 and a `mult(sqrt(neg(1)), NIPI)` form — neither matches the
shipped entry; the live upper bound on `main` is K=137.

Goal: try to shorten `pi` below K=137 via alternate mathematical identities
using the existing `WITNESSES` library (append-only rule — no new primitives,
no edits to sibling witnesses).

## Candidate identities evaluated

Each candidate was constructed by leaf substitution (`x`, `y` slots) into the
stored witness trees, then checked via
`equivalence_check(ast, "pi", samples=4096, tolerance=1e-10, domain="complex-box")`.

| # | Identity                              | K (tree) | Passed? | max\_diff | vs. 137 |
|---|---------------------------------------|---------:|:-------:|:---------:|--------:|
| A | `mult(neg(i), ln(neg(1)))`            |     145  |  yes    | 1.3e-15   | +8      |
| B | `acos(neg(1))`                        |     581  |  no*    | 3.7e-08   | +444    |
| C | `mult(2, asin(1))` with 2=add(1,1)    |     371  |  yes    | 0.0       | +234    |
| D | `mult(4, atan(1))` with 4=add(2,2)    |     473  |  yes    | 3.8e-15   | +336    |
| E | `mult(ln(neg(1)), inv(i))`            |     145  |  yes    | 4.9e-15   | +8      |
| F | `div(ln(neg(1)), i)`                  |     145  |  yes    | 4.9e-15   | +8      |

*B: acos witness's branch-cut handling at x=-1 (disk boundary) degrades to
1e-8, below the 1e-10 tolerance. Would need a reference callable change or a
different branch-cut path — out of scope.

## Why all candidates lose

The library's `i` witness itself ships at **K=91** and every "extract π from
`ln(-1) = iπ`" path has to multiply or divide by `i` (or `neg(i)` or `inv(i)`,
each K=107 after a K=17 unary wrap). The cheapest envelope is:

```
K(mult) - 2 + K(neg-of-i) + K(ln(-1))
= 17 - 2  + 107             + 23
= 145
```

That's already +8 over the 137-token direct construction, which bakes the
i/π staging into a shared 9-stage skeleton without paying two full `i`-witness
costs. Inverse trig (`asin`, `acos`, `atan`) starts at K ≥ 337 on its own —
they're products of an embedded `i` tree and so strictly worse here.

Paper Table 4 compiler upper bound is K=193 for `pi` (search floor >53). Our
K=137 already beats the compiler value by 56; the gap to the search floor
(≈84) is not crossable by compile-from-witnesses surgery alone. A tighter
bound would require either:
- a new primitive `i`-free identity (unlikely — `i = exp(iπ/2)` is circular;
  there is no real-only elementary identity for π that avoids `arctan`/`arcsin`/
  `arccos` which each internally carry `i`), or
- a bespoke `pi`-specific proof tree harvested directly (not via
  substitution) from a new proof-engine stage.

Both are beam-search / new-witness territory, not this surgery.

## Verdict

**Retain K=137.** No mutation to the `pi` entry.

Reproduce with `python3 /tmp/pi_candidates.py` (kept in-repo at this doc's
commit time for the record):

```
A: mult(neg(i), ln(-1)): K=145
B: acos(-1):             K=581 (fails tolerance)
C: 2*asin(1):            K=371
D: 4*atan(1):            K=473
E: mult(ln(-1), inv(i)): K=145
F: div(ln(-1), i):       K=145
```
