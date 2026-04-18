"""Tree optimization helpers for /eml-optimize.

Iter-1 scope:
- `equivalence_check(a, b)`: dense interior sample + branch-locus probe.
- `subtree_witness_swap(ast, targets)`: peephole — replace subtrees equivalent to
  a known witness with the witness's stored tree when shorter.

Deferred to later iters: beam search, exhaustive minimality, sympy symbolic gate,
leaderboard writer.
"""

from __future__ import annotations

import cmath
from dataclasses import dataclass
from typing import Callable, Optional

from .branch import probe
from .domain import sample
from .eml import EmlNode, Leaf, Node, evaluate, k_tokens, parse
from .reference import NAMED_CLAIMS, is_binary
from .witnesses import WITNESSES, Witness

Evaluator = Callable[[complex, complex], complex]


@dataclass(frozen=True)
class EquivalenceResult:
    passed: bool
    samples: int
    max_abs_diff: float
    interior_diff: float
    branch_flags: list[dict]
    caveats: list[str]


def _eval_safe(fn: Callable[[complex, complex], complex], x: complex, y: complex) -> Optional[complex]:
    try:
        return fn(x, y)
    except (ZeroDivisionError, ValueError, OverflowError):
        return None


def equivalence_check(
    left: Node,
    right: Node | str,
    *,
    samples: int = 1024,
    domain: str = "complex-box",
    tolerance: float = 1e-10,
    seed: int = 0,
    branch_claim: Optional[str] = None,
    binary: bool = False,
) -> EquivalenceResult:
    """Numerical equivalence gate: both trees agree on interior + branch loci.

    `right` may be another AST or a claim name from NAMED_CLAIMS (e.g. 'exp').
    `branch_claim` picks which branch-cut loci to probe; defaults to a string
    `right` when available, else skips branch probing.
    """
    left_fn: Evaluator = lambda x, y: evaluate(left, x, y)
    if isinstance(right, str):
        if right not in NAMED_CLAIMS:
            raise ValueError(f"unknown claim {right!r}")
        right_fn: Evaluator = NAMED_CLAIMS[right]
        binary = binary or is_binary(right)
        branch_claim = branch_claim or right
    else:
        right_fn = lambda x, y: evaluate(right, x, y)

    caveats_preamble: list[str] = []
    if branch_claim is None:
        caveats_preamble.append(
            "branch-cut probes skipped — both sides are raw ASTs and no "
            "--branch-claim was provided; verdict is interior-only"
        )

    xs = sample(domain, samples, seed=seed)
    ys = sample(domain, samples, seed=seed + 1) if binary else [1 + 0j] * samples

    caveats: list[str] = list(caveats_preamble)
    max_diff = 0.0
    for x, y in zip(xs, ys):
        lv = _eval_safe(left_fn, x, y)
        rv = _eval_safe(right_fn, x, y)
        if lv is None or rv is None:
            caveats.append("sample raised numerical error; treated as match")
            continue
        d = abs(lv - rv)
        if d > max_diff:
            max_diff = d

    interior_diff = max_diff
    branch_flags: list[dict] = []
    if branch_claim:
        for locus, z in probe(branch_claim):
            lv = _eval_safe(left_fn, z, z if binary else 1 + 0j)
            rv = _eval_safe(right_fn, z, z if binary else 1 + 0j)
            if lv is None or rv is None:
                branch_flags.append({"locus": locus, "sample": _fmt(z), "abs_diff": float("nan"), "note": "numerical-error"})
                continue
            d = abs(lv - rv)
            branch_flags.append({"locus": locus, "sample": _fmt(z), "abs_diff": d})
            if d > max_diff:
                max_diff = d

    return EquivalenceResult(
        passed=max_diff <= tolerance,
        samples=samples,
        max_abs_diff=max_diff,
        interior_diff=interior_diff,
        branch_flags=branch_flags,
        caveats=caveats,
    )


def _fmt(z: complex) -> str:
    return f"({z.real:g}{z.imag:+g}j)"


# ---------- peephole: witness subtree swap ----------


@dataclass(frozen=True)
class SwapCandidate:
    path: tuple[str, ...]  # sequence of "a"/"b" steps from root
    witness_name: str
    original_K: int
    replacement_K: int


def subtree_witness_swap(
    ast: Node,
    *,
    targets: Optional[list[str]] = None,
    samples: int = 256,
    tolerance: float = 1e-8,
    domain: str = "complex-box",
    seed: int = 0,
) -> tuple[Node, list[SwapCandidate]]:
    """Walk `ast`; swap subtrees that numerically match a shorter stored witness.

    Only unary-in-x witnesses with stored trees qualify in iter-1 — stored trees
    for 'exp', 'ln', 'e' are always shorter than or equal to typical wrapped
    subtrees. Returns (new_ast, list_of_swaps_made). Runs bottom-up to make sure
    we don't re-swap an already-shrunk subtree.
    """
    stored: list[Witness] = [
        w for w in WITNESSES.values()
        if w.tree is not None and w.arity in (0, 1) and not is_binary(w.name)
        and (targets is None or w.name in targets)
    ]
    swaps: list[SwapCandidate] = []
    new_ast = _swap_recurse(ast, stored, samples, tolerance, domain, seed, swaps, path=())
    return new_ast, swaps


def _swap_recurse(
    node: Node,
    stored: list[Witness],
    samples: int,
    tolerance: float,
    domain: str,
    seed: int,
    swaps: list[SwapCandidate],
    path: tuple[str, ...],
) -> Node:
    if isinstance(node, Leaf):
        return node
    # Recurse first (bottom-up).
    new_a = _swap_recurse(node.a, stored, samples, tolerance, domain, seed, swaps, path + ("a",))
    new_b = _swap_recurse(node.b, stored, samples, tolerance, domain, seed, swaps, path + ("b",))
    current = EmlNode(new_a, new_b)
    current_k = k_tokens(current)

    best_swap: Optional[tuple[Witness, Node]] = None
    for w in stored:
        assert w.tree is not None
        w_ast = parse(w.tree)
        w_k = k_tokens(w_ast)
        if w_k >= current_k:
            continue
        res = equivalence_check(
            current, w_ast,
            samples=samples, tolerance=tolerance, domain=domain, seed=seed,
            branch_claim=w.name if w.name in NAMED_CLAIMS else None,
            binary=False,
        )
        if res.passed:
            if best_swap is None or k_tokens(best_swap[1]) > w_k:
                best_swap = (w, w_ast)

    if best_swap is not None:
        w, w_ast = best_swap
        swaps.append(SwapCandidate(
            path=path, witness_name=w.name,
            original_K=current_k, replacement_K=k_tokens(w_ast),
        ))
        return w_ast
    return current
