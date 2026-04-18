# When the verdict is `cannot-verify` or `parse-error`

Not every identity reduces to something we can evaluate numerically. This page explains what each failure mode means and how to recover.

## `parse-error`

sympy refused to parse one of the sides. Most common causes:

- **Unbalanced parens / stray syntax** — `sin(x`, `x *+ 1`, etc.
- **Invalid LaTeX.** The LaTeX parser is sympy's; it's not as forgiving as Overleaf. Try Python syntax instead.
- **Using a symbol name that's also a sympy keyword** — rare but possible. Rename.

**Recovery:** reformat the expression. The skill's allowed identifiers are `x`, `y`, `e`, `pi`, `i`, and the elementary-function names `exp`, `log`/`ln`, `log10`, `sqrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`.

## `cannot-verify`

sympy parsed both sides, but at least one side can't be reduced to a numerical function of `(x, y)`. Most common causes:

- **Free symbols other than `x` and `y`.** `a + b == b + a` — true but symbolic. Substitute concrete symbol names or restrict to `x` and `y`.
- **Unsupported functions.** Gamma, Bessel, hypergeometric, `Piecewise`, integrals, sums, derivatives — sympy knows them symbolically but the identity checker's lambdify fallback may refuse.
- **Infinite-precision-required constants.** Symbolic constants like `Rational(1, 7)` work fine; `Integer(oo)` does not.

**Recovery options:**

1. Rename extra symbols to `x` and `y` (binary identities) or substitute concrete values.
2. For special functions, use sympy directly: `sympy.simplify(lhs - rhs)` or `sympy.trigsimp`.
3. If the identity is meant to hold over a restricted domain, pass `--domain positive-reals` or `--domain real-interval` to narrow the sampler.

## "verified" is numerical, not symbolic

`verified` means the two sides agreed on the chosen interior sample and all branch-probe points within the requested tolerance. This is a *very strong* indicator of truth for elementary functions (the failure mode is typically a hash-collision-style coincidence, which is astronomically unlikely at 1024 complex samples), but it is not a proof. For a formal proof:

- Use `sympy.simplify(lhs - rhs) == 0`, or `sympy.trigsimp`, `sympy.logcombine`, `sympy.radsimp`.
- Reach for a CAS (Mathematica, Maple) or a proof assistant (Lean, Rocq) for cases sympy can't close.

The skill is explicitly a screening step — most LLM-generated identities that are wrong fail numerically on the first sample, and most that pass a numerical audit are actually true.

## `branch-dependent` is a feature, not a warning

When you see `branch-dependent`, the identity holds on the principal branch (interior sample agrees) but disagrees at one of the catalogued branch-cut probe points. This is the honest answer for identities like:

- `log(x·y) == log(x) + log(y)` — holds on positive reals, picks up `2πi` off-sheet.
- `sqrt(x²) == x` — holds on the right half-plane, flips sign on the left.
- `asin(sin(x)) == x` — holds on `[-π/2, π/2]`, wraps outside.

Use `--domain positive-reals` (or another narrowing domain) if your application only cares about the principal branch.
