"""Calculator-primitive witness library.

For witnesses whose tree body is known axiomatically, we include the tree.
For the rest, we ship metadata only (K, depth, minimality, proof URL). When
`/eml-lab`'s compile mode lands, it fills in trees at call time.

K values and minimality claims are sourced from
https://yaniv-golan.github.io/proof-engine/ and arXiv:2603.21852.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class BranchAuditRecord:
    """Structured record of a branch-audit probe outcome on a single locus.

    Produced deterministically by `eml_core.branch_audit.build_summary`. Pinned
    onto library witnesses via P3.3 so the leaderboard (and any downstream
    consumer) no longer needs to substring-match on `Witness.note` to recover
    structured audit context.
    """

    domain: str            # canonical domain name (`auto_domain_for` of the claim)
    locus: str             # "no-cut" for entire functions / constants with a reference,
                           # else one of branch.probe()'s locus labels
    probes_total: int      # how many probe points contributed to this record
    probes_passed: int     # how many matched the reference within tolerance
    max_abs_diff: float    # worst |tree - ref| seen on the locus (0.0 if no probes ran)
    notes: Optional[str] = None


@dataclass(frozen=True)
class Witness:
    name: str
    arity: int  # 1 (unary in x), 2 (binary in x,y), or 0 (constant)
    K: int  # current-best RPN token count (upper bound unless minimal=True)
    depth: int
    minimal: bool  # proven minimal via exhaustive search?
    proof_url: Optional[str]
    tree: Optional[str]  # nested EML form, if known; None means "not stored"
    note: str = ""
    # --- leaderboard fields (iter-10, P2.1). Optional; defaults=None keep
    # existing keyword-only constructions unchanged. Back-fill sources cited
    # per-entry in code comments; None means "no published value in
    # docs/internal/kvalues.md". WITNESSES remains append-only: these are
    # additive schema fields, not mutations to RPN/domain/proof_url.
    paper_k: Optional[int] = None  # arXiv:2603.21852, Table 4 (compiler K)
    proof_engine_k: Optional[int] = None  # proof-engine page publishing per-primitive K
    verdict: Optional[str] = None  # "minimal" | "refuted-upward" | "upper-bound" | None
    # --- P3.3: structured branch-audit summary. Populated at module-load time
    # by `eml_core.branch_audit.build_summary`; empty tuple default keeps all
    # positional / existing-keyword constructors working unchanged.
    #
    # Design: constants (arity=0 → e, pi, i, apex) carry `()` because they
    # have no interior domain to sample and no cut to probe — their K-context
    # already pins verification and a zero-probe record would be noise.
    # Entire references (exp, sin, cos, add, mult, sub, div, pow, neg, inv,
    # tan) get a single `locus="no-cut"` record sampled from the canonical
    # domain. Branch-cut references (ln, log10, sqrt, asin, acos, atan) get
    # one baseline `no-cut` record on the canonical domain plus one record
    # per distinct locus returned by `branch.probe(claim)`.
    branch_audit_summary: tuple["BranchAuditRecord", ...] = field(default_factory=tuple)


WITNESSES: dict[str, Witness] = {
    # --- axioms (tree bodies are trivially known) ---
    "e": Witness(
        name="e",
        arity=0,
        K=3,
        depth=1,
        minimal=True,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/the-binary-operator-eml-is-defined-by-the-expression-text-eml-a-b-exp-a-ln-b/",
        tree="eml(1, 1)",
        note="axiom [1]",
        # kvalues.md row `e`: paper K=3/3, proof-engine K=3 (proof [1]).
        paper_k=3,
        proof_engine_k=3,
        verdict="minimal",
    ),
    "exp": Witness(
        name="exp",
        arity=1,
        K=3,
        depth=1,
        minimal=True,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/the-binary-operator-defined-by-text-eml-a-b-exp-a-ln-b-satisfies-text-eml-x-1/",
        tree="eml(x, 1)",
        note="axiom [2]; EXP identity",
        # kvalues.md row `exp`: paper K=3/3, proof-engine K=3 (proof [2]).
        paper_k=3,
        proof_engine_k=3,
        verdict="minimal",
    ),
    "ln": Witness(
        name="ln",
        arity=1,
        K=7,
        depth=3,
        minimal=True,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-triple-nesting-recovers-ln-x/",
        tree="eml(1, eml(eml(1, x), 1))",
        note="triple-nesting identity; principal-branch cmath; "
             "exhaustive minimality verified by minimality.py "
             "(no shorter tree matches ln on the default complex grid up to K=5)",
        # kvalues.md row `ln`: paper K=7/7, proof-engine K=7 (proof [3]).
        # minimality.py audit-minimality --target ln --max-k 7 enumerates
        # 2 unique functions at K=1, 4 at K=3, 16 at K=5, 80 at K=7;
        # ln first matches at K=7. Minimal by exhaustive cross-check.
        paper_k=7,
        proof_engine_k=7,
        verdict="minimal",
    ),
    # --- proven-minimal composites (trees sourced from proof-engine) ---
    "add": Witness(
        name="add",
        arity=2,
        K=19,
        depth=8,
        minimal=True,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-k19-addition-tree/",
        tree="eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(y, 1)), 1))",
        note="proven minimal via exhaustive search; valid on positive-reals (complex inputs cross branch cuts)",
        # kvalues.md row `add`: paper K=19/19, proof-engine K=19 (proof [4]).
        paper_k=19,
        proof_engine_k=19,
        verdict="minimal",
    ),
    "mult": Witness(
        name="mult",
        arity=2,
        K=17,
        depth=8,
        minimal=True,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-k17-multiplication-tree/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), y), 1)), 1)",
        note="proven minimal; removable singularity at x=e^e; holds on complex-box",
        # kvalues.md row `mult`: paper K=17/17, proof-engine K=17 (proof [5]).
        paper_k=17,
        proof_engine_k=17,
        verdict="minimal",
    ),
    # --- composed from closure-page formulas (sub = eml(LN(x), EXP(y))) ---
    "sub": Witness(
        name="sub",
        arity=2,
        K=11,
        depth=4,
        minimal=True,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(1, x), 1)), eml(y, 1))",
        note="sub = eml(LN(x), EXP(y)); confirmed minimal by iter-6 exhaustive enumeration at K<=11 (30,071 unique functions, 3.3 s)",
        # kvalues.md row `sub`: paper K=—/—, proof-engine K=— (via [7]).
        paper_k=None,
        proof_engine_k=None,
        verdict="minimal",
    ),
    "pow": Witness(
        name="pow",
        arity=2,
        K=25,
        depth=9,
        minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, y)), 1)), eml(1, eml(eml(1, x), 1))), 1)), 1), 1)",
        note="pow = EXP(MULT(y, LN(x))); closure-page upper bound, verified on small positive reals",
        # kvalues.md row `pow`: paper K=—/—, proof-engine K=— (via [7]).
        paper_k=None,
        proof_engine_k=None,
        verdict="upper-bound",
    ),
    # --- beam-discovered witnesses (iter-5: search + goal propagation) ---
    "neg": Witness(
        name="neg",
        arity=1,
        K=17,
        depth=6,
        minimal=False,
        proof_url=None,
        tree="eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1))",
        note="beam-discovered iter-5; paper K=15 upper bound not reproducible at K=15 "
        "with per_level_cap=100k (likely paper upper bound is wrong or uses a "
        "different sample grid). Equivalence max_diff < 1e-14 on complex-box.",
        # kvalues.md row `neg`: paper K=15 (compiler) / ≤15 (search); proof-engine —
        # via [7]. Verdict refuted-upward: iter-8 symbolic gate + iter-9 exhaustive
        # minimality at both 64/12 and 256/14 hash resolutions found no K=15 match.
        paper_k=15,
        proof_engine_k=None,
        verdict="refuted-upward",
    ),
    "inv": Witness(
        name="inv",
        arity=1,
        K=17,
        depth=6,
        minimal=False,
        proof_url=None,
        tree="eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), eml(eml(1, 1), 1)), 1)",
        note="beam-discovered iter-5; paper K=15 upper bound not reproducible. "
        "Equivalence max_diff < 1e-12 on complex-box.",
        # kvalues.md row `inv`: paper K=15 (compiler) / ≤15 (search); proof-engine —
        # via [7]. Same three-way refutation as neg.
        paper_k=15,
        proof_engine_k=None,
        verdict="refuted-upward",
    ),
    # --- upper-bound witnesses (compiler / hand-constructed) ---
    "pi": Witness(
        name="pi", arity=0, K=137, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/",
        tree=None, note="upper bound; paper reports K=193 compiler, >53 search",
    ),
    "i": Witness(
        name="i", arity=0, K=91, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/",
        tree=None, note="upper bound",
    ),
    "sqrt": Witness(
        name="sqrt", arity=1, K=59, depth=-1, minimal=False, proof_url=None,
        tree=None, note="upper bound; paper reports K=139 compiler, >=35 search",
    ),
    "log10": Witness(
        name="log10", arity=1, K=247, depth=-1, minimal=False, proof_url=None,
        tree=None, note="upper bound",
    ),
    "sin": Witness(
        name="sin", arity=1, K=471, depth=-1, minimal=False, proof_url=None,
        tree=None, note="upper bound",
    ),
    "cos": Witness(
        name="cos", arity=1, K=373, depth=-1, minimal=False, proof_url=None,
        tree=None, note="upper bound",
    ),
    "tan": Witness(
        name="tan", arity=1, K=915, depth=-1, minimal=False, proof_url=None,
        tree=None, note="upper bound",
    ),
    "asin": Witness(
        name="asin", arity=1, K=369, depth=-1, minimal=False, proof_url=None,
        tree=None, note="upper bound",
    ),
    "acos": Witness(
        name="acos", arity=1, K=565, depth=-1, minimal=False, proof_url=None,
        tree=None, note="upper bound",
    ),
    "atan": Witness(
        name="atan", arity=1, K=443, depth=-1, minimal=False, proof_url=None,
        tree=None, note="upper bound",
    ),
    "apex": Witness(
        name="apex", arity=0, K=-1, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree=None, note="closure-over-calculator-primitives apex proof",
        # Not a primitive — manifest pointer. No K of its own; verdict=None.
        paper_k=None, proof_engine_k=None, verdict=None,
    ),
}


class UnknownWitness(KeyError):
    """Raised when a lookup name is not in the witness library."""


def lookup(name: str) -> Witness:
    if name not in WITNESSES:
        raise UnknownWitness(
            f"unknown witness {name!r}; known: {sorted(WITNESSES)}"
        )
    return WITNESSES[name]


def names() -> list[str]:
    return sorted(WITNESSES)
# --- iter-3 harvest: trees for pi/i/sqrt/sin/cos/tan + new div witness ---
# Source: /tmp/harvest_all.py reproduces the proof-engine 9-stage pi/i
# construction and composes div/sqrt/sin/cos/tan from existing witnesses.
# Append-only; semantically overrides earlier tree=None entries via dict update.
WITNESSES.update({
    "i": Witness(
        name="i", arity=0, K=91, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/",
        tree="eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1)",
        note=(
            "harvested via 9-stage pi/i construction (proof.py reproduction); matches paper "
            "K=91. Equivalence max_diff < 1e-14 on complex-box. "
        ),
        # kvalues.md row `i`: paper K=— (Table 4 publishes no i entry per note),
        # proof-engine K=— (via proof [6] but no explicit per-constant K).
        paper_k=None, proof_engine_k=None, verdict="upper-bound",
    ),
    "pi": Witness(
        name="pi", arity=0, K=137, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1))), 1)), 1)",
        note=(
            "harvested via 9-stage pi/i construction (proof.py reproduction); matches paper "
            "K=137. Equivalence max_diff < 1e-14 on complex-box. "
        ),
        # kvalues.md row `pi`: paper K=193 (compiler), >53 (search); proof-engine
        # — (proof [6] but no explicit K). Use the compiler value as the
        # unambiguous scalar; the >53 search floor is noted in kvalues prose.
        paper_k=193, proof_engine_k=None, verdict="upper-bound",
    ),
    "sqrt": Witness(
        name="sqrt", arity=1, K=59, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, x), 1))), 1)), 1), 1)",
        note=(
            "harvested via exp(½·ln(x)); matches closure-page K=59. Equivalence max_diff < "
            "1e-13 on positive-reals (principal sqrt). "
        ),
        # kvalues.md row `sqrt`: paper K=139 (compiler), ≥35 (search); proof-engine
        # — (via [7]). Use compiler value 139 as the scalar.
        paper_k=139, proof_engine_k=None, verdict="upper-bound",
    ),
    "sin": Witness(
        name="sin", arity=1, K=399, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via (exp(ix)-exp(-ix))·inv(2i); K=399 beats closure-page K=471 by "
            "using inv directly. Equivalence max_diff < 1e-14 on real-interval; complex-box "
            "exposes branch-cut artifacts in inv composition. "
        ),
        # kvalues.md `sin` notes "beats Table 4's K=471 by 72" — Table 4 K=471.
        # Proof-engine K=— (via [7], no explicit per-primitive K published).
        paper_k=471, proof_engine_k=None, verdict="upper-bound",
    ),
    "cos": Witness(
        name="cos", arity=1, K=301, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via (exp(ix)+exp(-ix))·inv(2); K=301 beats closure-page K=373 by "
            "using inv directly. Equivalence max_diff < 1e-14 on real-interval; complex-box "
            "exposes branch-cut artifacts. "
        ),
        # kvalues.md `cos` notes "beats Table 4's K=373 by 72" — Table 4 K=373.
        paper_k=373, proof_engine_k=None, verdict="upper-bound",
    ),
    "tan": Witness(
        name="tan", arity=1, K=731, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via sin·inv(cos); K=731 beats closure-page K=915. Equivalence "
            "max_diff < 1e-14 on unit-disk-interior; poles of cos make real-interval too "
            "aggressive. "
        ),
        # kvalues.md `tan` notes "beats Table 4's K=915 by 184" — Table 4 K=915.
        paper_k=915, proof_engine_k=None, verdict="upper-bound",
    ),
    "div": Witness(
        name="div", arity=2, K=33, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), eml(eml(eml(1, eml(eml(1, eml(1, y)), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via x · inv(y); K=33 beats closure-page K=73 by using "
            "inv directly. Equivalence max_diff < 1e-13 on right-half-plane."
        ),
        # div is not listed as a standalone row in kvalues.md's primitives table
        # (it rides the closure-page via [7]); no paper/proof-engine per-primitive K.
        paper_k=None, proof_engine_k=None, verdict="upper-bound",
    ),
})
# --- iter-4 harvest: closure remaining four primitives ---
# Source: /tmp/harvest_iter4.py composes textbook formulas for the inverse
# trig functions and a constant-10 chain for log10. Append-only; later
# entries override earlier tree=None entries via dict update.
WITNESSES.update({
    "atan": Witness(
        name="atan", arity=1, K=403, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1)), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1), 1))), 1)), eml(x, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1)), 1)), eml(x, 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)), 1))), 1)), 1)",
        note=(
            "harvested via (i/2)·ln((i+x)/(i-x)); K=403 beats closure-page K=443. Equivalen"
            "ce max_diff < 1e-14 on real-interval. Branch-cut probes on imag-axis-outside-["
            "-i,i] skipped because the K=19 ADD/K=23 SUB witnesses themselves break for lar"
            "ge-imag complex inputs (see their own notes)."
        ),
        # kvalues.md iter-4 sub-table: atan paper Table 4 K=443 (our 403, saving 40).
        paper_k=443, proof_engine_k=None, verdict="upper-bound",
    ),
    "asin": Witness(
        name="asin", arity=1, K=337, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1), 1))), 1)), eml(eml(1, 1), 1)))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1))), 1)), 1), 1), 1)), 1))), 1))), 1)), 1)",
        note=(
            "harvested via -i·ln(ix + sqrt(1-x²)); K=337 beats closure-page K=369. Equivale"
            "nce max_diff < 1e-14 on unit-disk-interior. Branch-cut probes outside [-1,1] s"
            "kipped for the same ADD-witness reason as atan."
        ),
        # kvalues.md iter-4 sub-table: asin paper Table 4 K=369 (our 337, saving 32).
        paper_k=369, proof_engine_k=None, verdict="upper-bound",
    ),
    "acos": Witness(
        name="acos", arity=1, K=533, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1))), 1)), 1)), 1)), 1)), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1), 1))), 1)), eml(eml(1, 1), 1)))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1)), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1))), 1)), 1), 1), 1)), 1))), 1))), 1)), 1), 1))",
        note=(
            "harvested via π/2 − asin(x); K=533 beats closure-page K=565. Equivalence max_d"
            "iff < 1e-14 on unit-disk-interior. Branch-cut probes outside [-1,1] skipped fo"
            "r the same ADD-witness reason as asin."
        ),
        # kvalues.md iter-4 sub-table: acos paper Table 4 K=565 (our 533, saving 32).
        paper_k=565, proof_engine_k=None, verdict="upper-bound",
    ),
    "log10": Witness(
        name="log10", arity=1, K=207, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, x), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1)), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1)), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1)), 1)), 1)), 1))), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via ln(x)·inv(ln(10)) where 10 is built as add(add(add(2,2),2), add("
            "2,2)); K=207 beats closure-page K=247 by using inv directly. Equivalence max_d"
            "iff < 1e-14 on positive-reals; branch probes on negative real axis pass."
        ),
        # kvalues.md iter-4 sub-table: log10 paper Table 4 K=247 (our 207, saving 40).
        paper_k=247, proof_engine_k=None, verdict="upper-bound",
    ),
})

# --- P3.3: back-fill `branch_audit_summary` for every library witness. ---
# Deterministic; re-derivable by `eml_core.branch_audit.build_summary`. The
# pin test in `tests/test_branch_audit_summary.py` re-runs the builder and
# asserts round-trip equality. Not a hand-crafted table.
def _backfill_branch_audit_summaries() -> None:
    import dataclasses

    from .branch_audit import build_summary

    for _name, _w in list(WITNESSES.items()):
        WITNESSES[_name] = dataclasses.replace(
            _w, branch_audit_summary=build_summary(_w)
        )


_backfill_branch_audit_summaries()
