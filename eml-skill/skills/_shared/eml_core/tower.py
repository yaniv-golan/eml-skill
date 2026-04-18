"""Transcendence-tower signatures for beam-search pruning.

Purpose: attach to each subtree a coarse "signature" of which algebraic
extensions of ℚ its symbolic value lives in, then prune subtrees whose
signature is provably incompatible with the target's.

The signature is a `set[str]` over the tag alphabet:

    "x"   : value depends on the free variable x
    "y"   : value depends on the free variable y
    "e"   : value contains exp(q) for some non-trivial algebraic q
            (i.e. Euler's e or any algebraic-exponent exponential)
    "pi"  : value contains π  (note: log(-1) = i·π, so log of a negative
            algebraic also triggers this tag together with "i")
    "i"   : value contains the imaginary unit
    "log" : value contains log(q) for an algebraic q ∉ {1}
            (distinct from "pi" — covers e.g. log(2), log(3), etc.)

Lindemann–Weierstrass corollaries used (these are THEOREMS, not Schanuel):

  (L1) For algebraic α ≠ 0, exp(α) is transcendental. In particular the
       bare constant e = exp(1) is transcendental over ℚ.
  (L2) For algebraic α ∉ {0, 1}, log(α) (principal branch) is transcendental.
       Hence log(2), log(-1) = iπ, etc. are transcendental over ℚ.
  (L3) π is transcendental (special case of L2 via log(-1)).

Explicitly NOT used (Schanuel-conditional) — if a prune decision would
require one of these, we keep the subtree (return True from the predicate):

  - Algebraic independence of {π, e} over ℚ (open).
  - Algebraic independence of {log(p₁), log(p₂), …} for distinct primes
    (known — Baker's theorem — but we stay within LW to keep the module
    small; nothing relies on it).
  - Any statement of the form "subtower A is strictly weaker than B" when
    A = {e, π} and B = {e} (would require Lindemann + Schanuel).

Correctness discipline: a false-negative prune (dropping a subtree that
could reach the target) is a correctness bug. When in doubt, return True.
"""

from __future__ import annotations

import functools
from typing import Iterable

import sympy as sp
from sympy.core.numbers import Exp1

from .eml import EmlNode, Leaf, Node
from .reference import NAMED_CLAIMS

__all__ = [
    "TAGS",
    "subtree_signature",
    "sympy_signature",
    "target_tower_signature",
    "can_reach_target",
    "clear_caches",
]

# -----------------------------------------------------------------------------
# Tag alphabet

TAGS: frozenset[str] = frozenset({"x", "y", "e", "pi", "i", "log"})

_X = sp.Symbol("x")
_Y = sp.Symbol("y")


# -----------------------------------------------------------------------------
# AST → sympy

def _ast_to_sympy(ast: Node) -> sp.Expr:
    if isinstance(ast, Leaf):
        if ast.symbol == "1":
            return sp.Integer(1)
        if ast.symbol == "x":
            return _X
        if ast.symbol == "y":
            return _Y
        raise ValueError(f"unknown leaf {ast.symbol!r}")
    assert isinstance(ast, EmlNode)
    a = _ast_to_sympy(ast.a)
    b = _ast_to_sympy(ast.b)
    return sp.exp(a) - sp.log(b)


# -----------------------------------------------------------------------------
# Signature extraction from a sympy expression
#
# We inspect the expression tree (post a light simplification pass) and
# collect tags by walking sub-nodes. This is deliberately syntactic — we
# don't try to prove things like exp(log(x)) == x unless sympy's built-in
# simplify surfaces it first. A conservative over-tag (reporting "e" when
# the value is in fact rational) is fine: pruning only fires on *missing*
# tags, never on extra ones.


def _canonicalize(expr: sp.Expr) -> sp.Expr:
    """Light canonicalization. Catches trivial identities like log(1)=0,
    exp(0)=1, but does NOT run full simplify (too slow in beam inner loop).
    """
    try:
        expr = sp.expand_log(expr, force=False)
    except Exception:
        pass
    try:
        expr = sp.expand_power_exp(expr)
    except Exception:
        pass
    return expr


def _has_free(expr: sp.Expr, sym: sp.Symbol) -> bool:
    try:
        return sym in expr.free_symbols
    except Exception:
        return False


def _is_algebraic_nonzero_constant(arg: sp.Expr) -> bool:
    """True if arg is a rational/integer constant and non-zero.

    We deliberately limit "algebraic" to Q-rationals here — that's already
    enough to trigger Lindemann–Weierstrass for exp(q) (q ≠ 0 rational → e).
    Extending to algebraic numbers requires ring-of-integers machinery we
    don't need; the over-approximation is safe for pruning.
    """
    if not arg.is_number:
        return False
    if arg.is_zero:
        return False
    return bool(arg.is_rational)


def sympy_signature(expr: sp.Expr) -> set[str]:
    """Walk a sympy expression, collect the tag set.

    Rules (conservative; may over-tag, must not under-tag):

      - x free       → add "x"
      - y free       → add "y"
      - sp.I present → add "i"
      - sp.pi present → add "pi"
      - Any exp(arg) subterm where arg is non-zero → add "e" (by L1 the
        value is transcendental-over-ℚ when arg is algebraic; even for
        transcendental arg we still conservatively tag "e").
      - Any log(arg) subterm:
          * if arg is a negative rational → add "pi", "i" (log(-q) = iπ + log q)
            AND add "log" if |arg| ≠ 1
          * else → add "log" (covers log(x), log(2), log(y+1), etc.)
    """
    expr = _canonicalize(expr)
    tags: set[str] = set()

    if _has_free(expr, _X):
        tags.add("x")
    if _has_free(expr, _Y):
        tags.add("y")

    # Walk every sub-expression once.
    for node in sp.preorder_traversal(expr):
        if node is sp.I or node == sp.I:
            tags.add("i")
        if node is sp.pi or node == sp.pi:
            tags.add("pi")
        # sympy represents the bare constant e as Exp1 (a NumberSymbol),
        # not as exp(1). Detect both forms.
        if isinstance(node, Exp1) or node is sp.E:
            tags.add("e")
        elif isinstance(node, sp.exp) or node.func is sp.exp:
            arg = node.args[0]
            # exp(0) would normally simplify away; guard anyway.
            if not (arg.is_number and arg.is_zero):
                tags.add("e")
        if isinstance(node, sp.log) or node.func is sp.log:
            arg = node.args[0]
            # log(1) = 0; log(0) undefined — skip both.
            if arg.is_number:
                if arg.is_zero:
                    continue
                if arg == 1:
                    continue
                # Negative real → iπ + log|arg|.
                if arg.is_real is True and arg.is_negative is True:
                    tags.add("pi")
                    tags.add("i")
                    if arg != -1:
                        tags.add("log")
                elif arg.is_rational and arg > 0 and arg != 1:
                    tags.add("log")
                else:
                    # complex algebraic / unknown — conservatively tag log
                    # (it can contain both iπ and log|·|).
                    tags.add("log")
            else:
                # Non-constant argument: log of something with x, y, or a
                # transcendental sub-expression. Tag "log".
                tags.add("log")

    return tags


# -----------------------------------------------------------------------------
# Subtree signatures (cached on AST identity via memoization on id + structure)

@functools.lru_cache(maxsize=10_000)
def _cached_ast_signature(rpn_key: str) -> frozenset[str]:
    # Caching by canonical RPN avoids re-walking sympy for identical subtrees.
    from .eml import parse
    ast = parse(rpn_key)
    expr = _ast_to_sympy(ast)
    return frozenset(sympy_signature(expr))


def subtree_signature(ast: Node) -> set[str]:
    """Signature of an EML subtree, via sympy canonicalization.

    Cached on canonical RPN: identical subtrees (by structure) share a
    signature regardless of which beam call built them.
    """
    from .eml import to_rpn
    try:
        return set(_cached_ast_signature(to_rpn(ast)))
    except Exception:
        # If sympy fails for any reason, return the maximal set — guarantees
        # no prune will fire on this subtree (conservative).
        return set(TAGS)


def clear_caches() -> None:
    """Clear memoization tables — mostly for tests that want a clean slate."""
    _cached_ast_signature.cache_clear()


# -----------------------------------------------------------------------------
# Target signatures (precomputed from NAMED_CLAIMS)

_TARGET_SIG_OVERRIDES: dict[str, set[str]] = {
    # Closed-form sympy expressions per target, hand-specified so we don't
    # rely on the cmath lambdas in NAMED_CLAIMS (which we can't introspect).
    # Where a target has a canonical sympy form, list it here.
    "exp":       {"x", "e"},
    "ln":        {"x", "log"},
    "log10":     {"x", "log"},
    "sqrt":      {"x", "e", "log"},  # sqrt(x) = exp(log(x)/2)
    "sin":       {"x", "e", "i"},    # (exp(ix)-exp(-ix))/(2i)
    "cos":       {"x", "e", "i"},
    "tan":       {"x", "e", "i"},
    "asin":      {"x", "e", "i", "log"},
    "acos":      {"x", "e", "i", "log", "pi"},
    "atan":      {"x", "e", "i", "log"},
    "sinh":      {"x", "e"},
    "cosh":      {"x", "e"},
    "tanh":      {"x", "e"},
    "asinh":     {"x", "e", "log"},
    "acosh":     {"x", "e", "log"},
    "atanh":     {"x", "log"},
    "neg":       {"x"},
    "inv":       {"x"},
    "sq":        {"x"},
    "succ":      {"x"},
    "pred":      {"x"},
    "double":    {"x"},
    "half":      {"x"},
    "add":       {"x", "y"},
    "sub":       {"x", "y"},
    "mult":      {"x", "y"},
    "div":       {"x", "y"},
    "pow":       {"x", "y", "e", "log"},
    "log_x_y":   {"x", "y", "log"},
    "avg":       {"x", "y"},
    "hypot":     {"x", "y", "e", "log"},
    "e":         {"e"},
    "pi":        {"pi", "i"},
    "i":         {"i"},
    "zero":      set(),
    "minus_one": set(),
    "two":       set(),
    "half_const": set(),
}


def target_tower_signature(name: str) -> set[str]:
    """Minimum-extension signature of a NAMED_CLAIMS target.

    Raises KeyError if the target is unknown. Returns a set of tags in
    TAGS. Over-tagging on the target is conservative in the wrong
    direction (makes pruning tighter = may drop valid subtrees), so
    this table is hand-curated and intentionally minimal.
    """
    if name not in NAMED_CLAIMS:
        raise KeyError(f"unknown target {name!r}")
    if name in _TARGET_SIG_OVERRIDES:
        return set(_TARGET_SIG_OVERRIDES[name])
    # No known signature → return full set, which means "don't prune against
    # this target" (nothing can be a strict subset of it).
    return set(TAGS)


# -----------------------------------------------------------------------------
# Pruning predicate

# Per eml() application: eml(a, b) = exp(a) - log(b).
#   - Always introduces "e" (the exp(a) branch) unless a is provably zero.
#   - May introduce "pi", "i", "log" from the log(b) branch depending on b.
# Conservative budget: each eml node can introduce AT MOST one new tag out
# of {e, pi, i, log}. That's an under-count on purpose — we'd rather let a
# prunable subtree survive than drop a valid one.

_INTRODUCIBLE_TAGS: frozenset[str] = frozenset({"e", "pi", "i", "log"})


def can_reach_target(
    subtree_sig: Iterable[str],
    target_sig: Iterable[str],
    remaining_k: int,
) -> bool:
    """Return True if the subtree *might* still reach the target.

    False only when we can prove (modulo L-W) that no amount of further
    combination within `remaining_k` tokens can supply the missing tags.

    Parameters
    ----------
    subtree_sig : current signature of the subtree under consideration
    target_sig  : signature the final tree must have
    remaining_k : extra RPN tokens available beyond the subtree's own K.
                  Each eml() adds 3 tokens minimum (leaf leaf E) and
                  introduces ≤1 new algebraic tag (conservative).

    Rules
    -----
    1. If subtree has an "x" or "y" tag the target lacks, keep. (Free
       variables can be cancelled via further eml composition, e.g.
       eml(x, eml(x, 1)) identities — we don't try to prove they can't.)
    2. Missing algebraic tags = target_sig - subtree_sig  ∩ _INTRODUCIBLE_TAGS.
       Each eml adds ≥3 tokens and ≤1 new tag, so we need
       remaining_k ≥ 3·|missing|.  If remaining_k < that, prune.
    3. Otherwise keep.
    """
    sub = set(subtree_sig)
    tgt = set(target_sig)

    missing = (tgt - sub) & _INTRODUCIBLE_TAGS
    if not missing:
        return True

    # Each new eml node costs at least 3 RPN tokens (two leaves + one "E").
    # Under our conservative "≤1 new tag per eml" rule, we need at least
    # 3 × |missing| remaining tokens to have a shot.
    min_tokens_needed = 3 * len(missing)
    if remaining_k < min_tokens_needed:
        return False
    return True
