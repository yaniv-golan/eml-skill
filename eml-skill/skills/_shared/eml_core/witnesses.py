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
    paper_k: Optional[int] = None  # arXiv:2603.21852, Table 4 (primary scalar)
    proof_engine_k: Optional[int] = None  # proof-engine page publishing per-primitive K
    verdict: Optional[str] = None  # "minimal" | "refuted-upward" | "upper-bound" | None
    # --- P-paper-k-audit-2026-04-19: Table 4 provenance. Table 4 publishes
    # two K columns per row — "EML Compiler" (deterministic arithmetic artifact
    # of the paper's unoptimized prototype compiler, Subsect 4.1) and "Direct
    # search" (exhaustive-search result, often annotated `N (M)` where M is the
    # no-extended-reals variant, or `N ≥? >M` where M is a confirmed lower
    # bound with N's minimality unconfirmed). Conflating the two columns is a
    # research-planning hazard: compiler K is trivially reproducible via K
    # algebra (never a refutation target), whereas direct-search K is the real
    # gap. See docs/paper-sqrt-k139-note.md and docs/paper-k-audit-2026-04-19.md
    # for the full reconciliation.
    paper_k_source: Optional[str] = None  # "compiler" | "direct-search" | None
    paper_k_direct: Optional[int] = None  # direct-search K when both columns
    # are published and a separate scalar is wanted (e.g. sqrt compiler=139 vs
    # direct=43). None when only one column has a value.
    paper_k_direct_lower: Optional[int] = None  # confirmed lower-bound floor
    # from Table 4's `>M` annotations (e.g. sqrt direct = "43 ≥? >35" →
    # paper_k_direct=43, paper_k_direct_lower=35). None when no floor published.
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
        # Table 4 Constants section: `e  3  3` — both columns agree.
        paper_k=3,
        proof_engine_k=3,
        verdict="minimal",
        paper_k_source="compiler",
        paper_k_direct=3,
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
        # Table 4 Function section: `e^x  3  3` — both columns agree.
        paper_k=3,
        proof_engine_k=3,
        verdict="minimal",
        paper_k_source="compiler",
        paper_k_direct=3,
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
        # Table 4 Function section: `ln x  7  7` — both columns agree.
        paper_k=7,
        proof_engine_k=7,
        verdict="minimal",
        paper_k_source="compiler",
        paper_k_direct=7,
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
        # Table 4 Operator section: `x+y  27  19 (19)` — compiler=27,
        # direct-search=19. Our paper_k=19 matches direct-search.
        paper_k=19,
        proof_engine_k=19,
        verdict="minimal",
        paper_k_source="direct-search",
        paper_k_direct=19,
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
        # Table 4 Operator section: `x×y  41  17 (17)` — compiler=41,
        # direct-search=17. Our paper_k=17 matches direct-search.
        paper_k=17,
        proof_engine_k=17,
        verdict="minimal",
        paper_k_source="direct-search",
        paper_k_direct=17,
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
        # Correction (P-paper-k-audit-2026-04-19): Table 4 Operator section
        # DOES publish `x−y  83  11 (11)` — compiler=83, direct-search=11.
        # Our shipped K=11 is exhaustively proven minimal and matches
        # Table 4's direct-search column. Backfill paper_k=11 as a new
        # published value we were previously missing.
        paper_k=11,
        proof_engine_k=11,
        verdict="minimal",
        paper_k_source="direct-search",
        paper_k_direct=11,
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
        # Correction (P-paper-k-audit-2026-04-19): Table 4 Operator section
        # DOES publish `x^y  49  25` — compiler=49, direct-search=25 (no
        # parenthetical, no lower bound). Our K=25 matches direct-search.
        # Backfill paper_k=25 as a new published value we were missing.
        paper_k=25,
        proof_engine_k=25,
        verdict="upper-bound",
        paper_k_source="direct-search",
        paper_k_direct=25,
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
        note="beam-discovered iter-5; paper K=15 not reproducible under "
        "IEEE-754 cmath (this repo's evaluator): no tree in the 2.1M-unique "
        "K=15 pool matches. Paper's K=15 is reproducible only under "
        "extended-reals semantics (Mathematica log(0)=-inf, exp(-inf)=0). "
        "Extended-reals K=15 witness: "
        "eml(eml(1, eml(1, eml(1, eml(eml(1,1), 1)))), eml(x, 1)) — the "
        "A-subtree evaluates through log(0)->-inf->+inf->-inf, which cmath "
        "rejects. See docs/refutation-neg-inv-k15.md 'Audit — extended reals'. "
        "K=17 shipped here is shortest IEEE-finite witness; equivalence "
        "max_diff < 1e-14 on complex-box.",
        # kvalues.md row `neg`: paper K=15 (compiler) / ≤15 (search); proof-engine —
        # via [7]. Verdict refuted-upward: iter-8 symbolic gate + iter-9 exhaustive
        # minimality at both 64/12 and 256/14 hash resolutions found no K=15 match.
        # Correction (P-paper-k-audit-2026-04-19): kvalues.md was wrong about
        # the compiler column — Table 4 Function section publishes `−x  57  15`
        # (compiler=57, direct-search=15). Our paper_k=15 is direct-search,
        # not compiler. The 🔴 refutation concerns the direct-search K=15.
        paper_k=15,
        proof_engine_k=None,
        verdict="refuted-upward",
        paper_k_source="direct-search",
        paper_k_direct=15,
    ),
    "inv": Witness(
        name="inv",
        arity=1,
        K=17,
        depth=6,
        minimal=False,
        proof_url=None,
        tree="eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), eml(eml(1, 1), 1)), 1)",
        note="beam-discovered iter-5; paper K=15 not reproducible under "
        "IEEE-754 cmath (refuted: 2.1M-unique K=15 pool, no match). "
        "Reproducible only under extended-reals semantics. "
        "Extended-reals K=15 witness: "
        "eml(eml(eml(1, eml(1, eml(1, eml(eml(1,1), 1)))), x), 1) — same "
        "A-subtree as neg's, reaches log(0)=-inf. See "
        "docs/refutation-neg-inv-k15.md. K=17 shipped is shortest IEEE-finite; "
        "equivalence max_diff < 1e-12 on complex-box.",
        # kvalues.md row `inv`: paper K=15 (compiler) / ≤15 (search); proof-engine —
        # via [7]. Same three-way refutation as neg.
        # Correction (P-paper-k-audit-2026-04-19): Table 4 Function section
        # publishes `1/x  65  15` (compiler=65, direct-search=15). Our
        # paper_k=15 is direct-search, not compiler.
        paper_k=15,
        proof_engine_k=None,
        verdict="refuted-upward",
        paper_k_source="direct-search",
        paper_k_direct=15,
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
        name="i", arity=0, K=75, depth=23, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/",
        tree="eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)",
        note=(
            "i-cascade 2026-04-19: re-derived as sqrt(neg(1)) = exp(½·ln(-1)) "
            "= exp(iπ/2) = i using the K=59 sqrt witness and the K=17 "
            "beam-discovered neg witness; K = 59 + (17 - 1) = 75, shorter by "
            "16 tokens than the published 9-stage K=91 construction. "
            "Equivalence max_abs_diff ~2.7e-16 on complex-box (samples=4096, "
            "tolerance=1e-10). Paper Table 4 Constants row `i  131  >55` — "
            "compiler K=131 (beaten by 56 tokens) with a direct-search lower "
            "bound >55 that our K=75 still respects. Previous note: harvested "
            "via 9-stage pi/i construction at K=91; replaced in favor of the "
            "sqrt/neg composition because the 16-token savings cascade into "
            "every downstream witness embedding i (sin, cos, tan, asin, acos, "
            "atan, and the three complex-box-honest inverse-trig variants)."
        ),
        # kvalues.md row `i`: paper K=— (Table 4 publishes no i entry per note),
        # proof-engine K=— (via proof [6] but no explicit per-constant K).
        # Correction (P-paper-k-audit-2026-04-19): Table 4 Constants section
        # DOES publish `i  131  >55` — compiler=131, direct-search has no
        # concrete K but a confirmed lower bound >55. Backfill paper_k=131
        # (compiler) with direct_lower=55 as a new published value we missed.
        paper_k=131, proof_engine_k=91, verdict="upper-bound",
        paper_k_source="compiler",
        paper_k_direct=None,
        paper_k_direct_lower=55,
    ),
    "pi": Witness(
        name="pi", arity=0, K=121, depth=31, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1))), 1)), 1)",
        note=(
            "harvested via mult(sqrt(-1), NIPI) where NIPI=-iπ is the K=31 subtree "
            "reused verbatim from the proof-engine 9-stage pi construction, and "
            "sqrt(-1)=i is derived from the K=59 sqrt witness composed with the "
            "K=17 beam-discovered neg witness (sqrt(neg(1))=i at K=75). This yields "
            "pi = mult(i_new, NIPI) at K = 17 + (75-1) + (31-1) = 121, saving 16 "
            "tokens vs the published K=137 (mult(i_k91, NIPI_k31)). The key lever "
            "is that the proof-engine's K=91 i tree uses an explicit construction, "
            "whereas sqrt(neg(1)) = exp(½·ln(-1)) = exp(iπ/2) = i is a shorter "
            "identity once our neg witness (K=17, beam iter-5) is available. "
            "The closure-page explicitly states K=137 is an open upper bound. "
            "Equivalence max_abs_diff < 1e-15 on complex-box/real-interval "
            "(samples=4096, tol=1e-10). "
        ),
        # kvalues.md row `pi`: paper K=193 (compiler), >53 (search); proof-engine
        # — (proof [6] but no explicit K). Use the compiler value as the
        # unambiguous scalar; the >53 search floor is noted in kvalues prose.
        # Table 4 Constants: `π  193  >53` — compiler=193, direct-search floor 53.
        paper_k=193, proof_engine_k=137, verdict="upper-bound",
        paper_k_source="compiler",
        paper_k_direct=None,
        paper_k_direct_lower=53,
    ),
    "sqrt": Witness(
        name="sqrt", arity=1, K=59, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, x), 1))), 1)), 1), 1)",
        note=(
            "harvested via exp(½·ln(x)); matches closure-page K=59. Equivalence max_diff < "
            "1e-13 on positive-reals (principal sqrt). Paper Table 4 reports compiler K=139 "
            "(deterministic artifact of applying paper's prototype compiler to the textbook "
            "identity — K=3+1*((41+(91-1)+(7-1))-1)=139 from paper's stated primitive Ks) "
            "and direct-search K=43 (annotated ≥? >35). Our K=59 is 16 tokens longer than "
            "paper's direct-search claim; follow-up P-sqrt-harvest-k43 tracks closing that "
            "gap. See docs/paper-sqrt-k139-note.md for the full reconciliation."
        ),
        # kvalues.md row `sqrt`: paper K=139 (compiler), ≥35 (search); proof-engine
        # — (via [7]). Use compiler value 139 as the scalar.
        # Table 4 Function: `√x  139  43 ≥? >35` — compiler=139,
        # direct-search K=43 (minimality unconfirmed, ≥? annotation) with
        # confirmed floor >35. See docs/paper-sqrt-k139-note.md for full
        # reconciliation.
        paper_k=139, proof_engine_k=59, verdict="upper-bound",
        paper_k_source="compiler",
        paper_k_direct=43,
        paper_k_direct_lower=35,
    ),
    "sin": Witness(
        name="sin", arity=1, K=351, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via (exp(ix)-exp(-ix))·inv(2i); i-cascade 2026-04-19 "
            "shrank this witness from K=399 → K=351 (delta -48) by substituting "
            "the new K=75 i subtree (sqrt(neg(1))) for the old K=91 9-stage "
            "i in its three occurrences. Beats closure-page K=471 by 120 using "
            "inv directly plus the i-cascade. Equivalence max_diff < 1e-14 on "
            "real-interval; complex-box exposes branch-cut artifacts in inv "
            "composition. "
        ),
        # kvalues.md `sin` notes "beats Table 4's K=471 by 72" — Table 4 K=471.
        # Proof-engine K=— (via [7], no explicit per-primitive K published).
        # Audit correction (P-paper-k-audit-2026-04-19): sin is **not** in
        # Table 4. The K=471 value originated in the `eml-calculator-closure`
        # proof-engine page (not the paper), was mis-cited as Table 4 in a
        # library comment, and has been shipping as paper_k ever since.
        # The paper_k=471 scalar is preserved unchanged (the value still
        # documents our harvest baseline) but paper_k_source=None flags the
        # mis-attribution: there is no verifiable Table 4 provenance.
        paper_k=471, proof_engine_k=471, verdict="upper-bound",
        paper_k_source=None,
    ),
    "cos": Witness(
        name="cos", arity=1, K=269, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via (exp(ix)+exp(-ix))·inv(2); i-cascade 2026-04-19 "
            "shrank this witness from K=301 → K=269 (delta -32) by substituting "
            "the new K=75 i subtree (sqrt(neg(1))) for the old K=91 9-stage "
            "i in its two occurrences. Beats closure-page K=373 by 104 using "
            "inv directly plus the i-cascade. Equivalence max_diff < 1e-14 on "
            "real-interval; complex-box exposes branch-cut artifacts. "
        ),
        # kvalues.md `cos` notes "beats Table 4's K=373 by 72" — Table 4 K=373.
        # Audit correction (P-paper-k-audit-2026-04-19): cos is **not** in
        # Table 4 — same mis-attribution pattern as sin. K=373 is a
        # closure-proof-page value, not a Table 4 value. paper_k_source=None.
        paper_k=373, proof_engine_k=373, verdict="upper-bound",
        paper_k_source=None,
    ),
    "tan": Witness(
        name="tan", arity=1, K=651, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via sin·inv(cos); i-cascade 2026-04-19 shrank this "
            "witness from K=731 → K=651 (delta -80) by substituting the new "
            "K=75 i subtree (sqrt(neg(1))) for the old K=91 9-stage i in its "
            "five occurrences. Beats closure-page K=915 by 264 via inv "
            "+ i-cascade. Equivalence max_diff < 1e-14 on unit-disk-interior; "
            "poles of cos make real-interval too aggressive. "
        ),
        # kvalues.md `tan` notes "beats Table 4's K=915 by 184" — Table 4 K=915.
        # Audit correction (P-paper-k-audit-2026-04-19): tan is **not** in
        # Table 4. K=915 is a closure-proof-page value. paper_k_source=None.
        paper_k=915, proof_engine_k=915, verdict="upper-bound",
        paper_k_source=None,
    ),
    "div": Witness(
        name="div", arity=2, K=17, depth=6, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(eml(1, eml(eml(1, eml(1, y)), 1)), eml(eml(1, x), 1)), 1)",
        note=(
            "harvested via /eml-optimize beam search (iter-5, --seed-witnesses "
            "--seed-subtrees) on right-half-plane at per-level-cap=200000; K=17 "
            "found in 33s matching paper Table 4's K=17. Supersedes the iter-3 "
            "x·inv(y) K=33 composition. Equivalence max_abs_diff < 2e-14 on "
            "right-half-plane over 4096 samples; div has no declared branch-cut "
            "probes in branch.py so branch_flags == []."
        ),
        # Paper Table 4 reports K=17 for x/y (direct-search value, no extended-
        # reals parenthetical). This entry now matches that bound.
        # Table 4 Operator section: `x/y  105  17 (17)` — compiler=105,
        # direct-search=17. Our paper_k=17 matches direct-search.
        paper_k=17, proof_engine_k=73, verdict="upper-bound",
        paper_k_source="direct-search",
        paper_k_direct=17,
    ),
})
# --- iter-4 harvest: closure remaining four primitives ---
# Source: /tmp/harvest_iter4.py composes textbook formulas for the inverse
# trig functions and a constant-10 chain for log10. Append-only; later
# entries override earlier tree=None entries via dict update.
WITNESSES.update({
    "atan": Witness(
        name="atan", arity=1, K=355, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1), 1))), 1)), eml(x, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), eml(x, 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)), 1))), 1)), 1)",
        note=(
            "harvested via (i/2)·ln((i+x)/(i-x)); i-cascade 2026-04-19 "
            "shrank this witness from K=403 → K=355 (delta -48) by "
            "substituting the new K=75 i subtree (sqrt(neg(1))) for the old "
            "K=91 9-stage i in its three occurrences. Beats closure-page "
            "K=443 by 88. Equivalence max_diff < 1e-14 on real-interval. "
            "Branch-cut probes on imag-axis-outside-[-i,i] skipped because "
            "the K=19 ADD/K=23 SUB witnesses themselves break for large-imag "
            "complex inputs (see their own notes)."
        ),
        # kvalues.md iter-4 sub-table: atan paper Table 4 K=443 (our 403, saving 40).
        # Audit correction (P-paper-k-audit-2026-04-19): atan is **not** in
        # Table 4. K=443 is a closure-proof-page value. paper_k_source=None.
        paper_k=443, proof_engine_k=443, verdict="upper-bound",
        paper_k_source=None,
    ),
    "asin": Witness(
        name="asin", arity=1, K=305, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1), 1))), 1)), eml(eml(1, 1), 1)))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1))), 1)), 1), 1), 1)), 1))), 1))), 1)), 1)",
        note=(
            "harvested via -i·ln(ix + sqrt(1-x²)); i-cascade 2026-04-19 "
            "shrank this witness from K=337 → K=305 (delta -32) by "
            "substituting the new K=75 i subtree (sqrt(neg(1))) for the old "
            "K=91 9-stage i in its two occurrences. Beats closure-page "
            "K=369 by 64. Equivalence max_diff < 1e-14 on unit-disk-interior. "
            "Branch-cut probes outside [-1,1] skipped for the same ADD-witness "
            "reason as atan."
        ),
        # kvalues.md iter-4 sub-table: asin paper Table 4 K=369 (our 337, saving 32).
        # Audit correction (P-paper-k-audit-2026-04-19): asin is **not** in
        # Table 4. K=369 is a closure-proof-page value. paper_k_source=None.
        paper_k=369, proof_engine_k=369, verdict="upper-bound",
        paper_k_source=None,
    ),
    "acos": Witness(
        name="acos", arity=1, K=485, depth=-1, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1))), 1)), 1)), 1)), 1)), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1), 1))), 1)), eml(eml(1, 1), 1)))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1))), 1)), 1), 1), 1)), 1))), 1))), 1)), 1), 1))",
        note=(
            "harvested via π/2 − asin(x); i-cascade 2026-04-19 shrank this "
            "witness from K=533 → K=485 (delta -48) by substituting the new "
            "K=75 i subtree (sqrt(neg(1))) for the old K=91 9-stage i in "
            "its three occurrences. Beats closure-page K=565 by 80. "
            "Equivalence max_diff < 1e-14 on unit-disk-interior. Branch-cut "
            "probes outside [-1,1] skipped for the same ADD-witness reason as "
            "asin."
        ),
        # kvalues.md iter-4 sub-table: acos paper Table 4 K=565 (our 533, saving 32).
        # Audit correction (P-paper-k-audit-2026-04-19): acos is **not** in
        # Table 4. K=565 is a closure-proof-page value. paper_k_source=None.
        paper_k=565, proof_engine_k=565, verdict="upper-bound",
        paper_k_source=None,
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
        # Audit correction (P-paper-k-audit-2026-04-19): log10 is **not** in
        # Table 4 as a distinct row. Table 4 has `logx y  117  29` (arbitrary-
        # base log binary operator) — not log10. K=247 originates from the
        # closure-proof-page. paper_k_source=None.
        paper_k=247, proof_engine_k=247, verdict="upper-bound",
        paper_k_source=None,
    ),
})

# --- iter-11 harvest: Table 1 primitives avg and hypot ---
# Source: paper Table 1 (scientific-calculator starting list) + Table 4
# (direct-search K >27 for both; compiler K=287 for avg, K=175 for hypot).
# avg = mult(add(x, y), inv(add(1, 1))); K=69 measured via k_tokens(parse(tree)).
# hypot = sqrt(add(mult(x, x), mult(y, y))); K=109 measured similarly.
# Both beat the paper's compiler K (69 << 287; 109 << 175) by composing from
# already-harvested witnesses. Append-only.
WITNESSES.update({
    "avg": Witness(
        name="avg", arity=2, K=69, depth=18, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(y, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "avg(x, y) = (x + y) / 2 composed as mult(add(x,y), inv(add(1,1))). "
            "K=69 beats paper Table 4 compiler K=287 by ~4×. Paper direct search "
            "ran out of budget at K>27 (no explicit tree). Equivalence max_diff < "
            "1e-13 on positive-reals (add witness inherits ln/exp positive-reals "
            "constraint; complex-box exhibits add-witness branch-cut artifacts)."
        ),
        # Table 4 Operator section: `(x+y)/2  287  >27` — compiler=287,
        # direct-search timed out with floor >27.
        paper_k=287, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="compiler",
        paper_k_direct=None,
        paper_k_direct_lower=27,
    ),
    "hypot": Witness(
        name="hypot", arity=2, K=109, depth=24, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, y)), 1)), y), 1)), 1), 1)), 1))), 1))), 1)), 1), 1)",
        note=(
            "hypot(x, y) = sqrt(x² + y²) composed as sqrt(add(mult(x,x), mult(y,y))). "
            "K=109 beats paper Table 4 compiler K=175. Paper direct search ran "
            "out of budget at K>27 (no explicit tree). Equivalence max_diff < "
            "1e-14 on unit-disk-interior; positive-reals triggers exp-overflow "
            "for inputs above ~30 via the add-of-squares intermediate."
        ),
        # Table 4 Operator section: `√(x²+y²)  175  >27` — compiler=175,
        # direct-search timed out with floor >27.
        paper_k=175, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="compiler",
        paper_k_direct=None,
        paper_k_direct_lower=27,
    ),
})

# --- iter-11 harvest: hyperbolic family (sinh/cosh/tanh/asinh/acosh/atanh) ---
# Source: /tmp/harvest_hyperbolic.py composes the six hyperbolics from existing
# witnesses (exp, add, sub, mult, inv, sqrt, ln, neg). Append-only. Each entry
# cites the closure-proof URL because these are derived compositions with the
# same provenance as sin/cos/tan. paper_k/proof_engine_k left None — arXiv
# Table 4 does not publish hyperbolic K values. verdict="upper-bound".
#
# Domain notes:
#   sinh/cosh/tanh — real-interval / unit-disk-interior; complex-box leaks
#     2π via the inherited add/sub witness (documented in their own notes).
#   asinh — real-interval / unit-disk-interior; same inheritance caveat.
#   acosh — positive-reals (requires x >= 1; the composite inherits add/sub's
#     positive-reals constraint which also happens to be the function's
#     principal-branch natural domain for real x).
#   atanh — unit-disk-interior (|x| < 1, matching the function's natural cut).
WITNESSES.update({
    "sinh": Witness(
        name="sinh", arity=1, K=81, depth=18, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(x, 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via (exp(x) - exp(-x))·inv(2); K=81. Equivalence max_diff < 1e-13 on "
            "real-interval and unit-disk-interior; complex-box leaks 2π via inherited ADD/SUB "
            "positive-reals constraint."
        ),
        paper_k=None, proof_engine_k=None, verdict="upper-bound",
    ),
    "cosh": Witness(
        name="cosh", arity=1, K=89, depth=19, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(x, 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via (exp(x) + exp(-x))·inv(2); K=89. Equivalence max_diff < 1e-13 on "
            "real-interval and unit-disk-interior; complex-box leaks 2π via inherited ADD/SUB "
            "positive-reals constraint."
        ),
        paper_k=None, proof_engine_k=None, verdict="upper-bound",
    ),
    "tanh": Witness(
        name="tanh", arity=1, K=201, depth=29, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(x, 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(x, 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via sinh·inv(cosh); K=201. Equivalence max_diff < 1e-14 on unit-disk-"
            "interior and real-interval; complex-box leaks via inherited ADD/SUB constraint."
        ),
        paper_k=None, proof_engine_k=None, verdict="upper-bound",
    ),
    "asinh": Witness(
        name="asinh", arity=1, K=117, depth=31, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1)), eml(1, 1)), 1))), 1))), 1)), 1), 1), 1)), 1))), 1))",
        note=(
            "harvested via ln(x + sqrt(x² + 1)); K=117. Equivalence max_diff < 1e-13 on "
            "real-interval and unit-disk-interior. Branch-cut probes on imag-axis-outside-"
            "[-i,i] skipped because inherited ADD witness breaks for large-imag inputs."
        ),
        paper_k=None, proof_engine_k=None, verdict="upper-bound",
    ),
    "acosh": Witness(
        name="acosh", arity=1, K=109, depth=30, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1)), 1)), eml(1, 1))), 1))), 1)), 1), 1), 1)), 1))), 1))",
        note=(
            "harvested via ln(x + sqrt(x² - 1)); K=109. Equivalence max_diff < 1e-14 on "
            "positive-reals (function requires x ≥ 1 on principal branch; positive-reals "
            "samples x ∈ (1e-3, 50) and the composite tree analytically agrees with "
            "cmath.acosh across the full range including the x<1 imaginary extension)."
        ),
        paper_k=None, proof_engine_k=None, verdict="upper-bound",
    ),
    "atanh": Witness(
        name="atanh", arity=1, K=101, depth=23, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/",
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(x, 1)), 1))), 1))), 1)), eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(x, 1))), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)",
        note=(
            "harvested via (ln(1+x) - ln(1-x))·inv(2); K=101. Equivalence max_diff < 1e-14 "
            "on unit-disk-interior (|x| < 1, matching the function's natural branch)."
        ),
        paper_k=None, proof_engine_k=None, verdict="upper-bound",
    ),
})

# --- complex-box-honest ADD (beam-discovered, append-only) ---
# The proven-minimal K=19 `add` witness only holds on positive-reals; on
# complex-box it carries an exact-2π log-branch gap. This entry is a
# higher-K cousin that passes equivalence_check on *both* complex-box and
# positive-reals at tol=1e-10, samples=4096. Discovered by beam_search
# with target='add', domain='complex-box', per_level_cap=100000,
# max_k=29, time_budget_s=1800, seed_witnesses=True (strategy=targeted,
# generalized scan) in 619 s over 432,195 candidates.
WITNESSES.update({
    "add_complex_box": Witness(
        name="add_complex_box",
        arity=2,
        K=27,
        depth=8,
        minimal=False,
        proof_url=None,
        tree="eml(eml(1, eml(eml(1, x), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(y, 1))), 1)), eml(eml(1, 1), 1)), 1))",
        note=(
            "beam-discovered complex-box-honest ADD. Proven-minimal `add` at "
            "K=19 has an exact-2π gap on complex-box from log-branch crossings; "
            "this K=27 upper bound closes that gap. Equivalence max_diff "
            "~3e-15 on complex-box, ~1.5e-14 on positive-reals (samples=4096, "
            "tolerance=1e-10). Methodology: /eml-optimize beam_search with "
            "per_level_cap=100000, max_k=29, seed_witnesses=True; no published "
            "proof-engine/paper K for complex-box-honest ADD."
        ),
        paper_k=None,
        proof_engine_k=None,
        verdict="upper-bound",
    ),
})

# --- complex-box-honest SUB + inverse trig family (append-only) ---
# Derived from add_complex_box. The K=11 `sub` witness uses
# `eml(LN(x), EXP(y)) = x - log(exp(y))` which only agrees with
# mathematical subtraction when |Im(y)| < π (principal strip). That's fine
# on the complex-box domain sampler (|Im(y)| < 2) and for cases where `y`
# is itself bounded (atan's i±x: |Im| ≤ 3 < π), but breaks when y can have
# larger imaginary magnitude — e.g. sub(1, x²) with x ∈ complex-box can hit
# |Im(x²)| ≈ 8 and desynchronizes the formula from cmath.sub.
#
# sub_complex_box(x, y) = add_complex_box(x, neg(y)). Composed from the
# beam-discovered K=27 add_complex_box and the K=17 neg witness; instantiation
# cost is 27 + 17 − 1 = 43 (the neg's x-slot is substituted, eliminating one
# leaf-token). Equivalence max_diff ~3e-15 on complex-box, ~1.5e-14 on
# positive-reals.
#
# Inverse-trig witnesses below use sub_complex_box (inlined as
# add_complex_box(a, neg(b))) to keep 1-x² and related differences honest on
# complex-box. asin and acos additionally avoid the squaring step by
# factoring sqrt(1-x²) = sqrt(1-x)·sqrt(1+x) — mathematically exact on the
# principal branch (verified numerically to 8e-16 across 1000 complex-box
# samples) and structurally necessary because after add_complex_box(a, neg(b))
# the internal log(exp(·)) still assumes |Im(y)| < π, which |Im(x²)| can
# exceed on complex-box. atan's i+x uses add_complex_box (|Im(i+x)| can reach
# 3, beyond the K=19 add's positive-reals safe zone); i-x keeps the K=11 sub
# because |Im(i-x)| ≤ 3 < π stays inside sub's principal-strip assumption.
#
# K cost vs existing (natural-domain) witnesses (post-i-cascade 2026-04-19):
#   asin:  305 → 429  (1.41× longer, complex-box-honest)
#   acos:  485 → 429  (shorter — uses direct -i·ln(x + i·sqrt(...)) instead of
#                       π/2 − asin, which paid a mult+pi surcharge)
#   atan:  355 → 355  (same K — the K=19 add was the only offender; swapping
#                       it for add_complex_box inflated one subtree but the
#                       shape of atan's formula kept the total unchanged)
# (pre-i-cascade ratios were asin 337→461, acos 533→461, atan 403→403; the
#  cascade shrank both sides proportionally so the ratios barely changed.)
WITNESSES.update({
    "sub_complex_box": Witness(
        name="sub_complex_box",
        arity=2,
        K=43,
        depth=14,
        minimal=False,
        proof_url=None,
        tree="eml(eml(1, eml(eml(1, x), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(y, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1))",
        note=(
            "complex-box-honest SUB derived as add_complex_box(x, neg(y)). "
            "Equivalence max_diff ~3.1e-15 on complex-box, ~1.5e-14 on "
            "positive-reals (samples=4096, tolerance=1e-10). Use when the "
            "`y` argument can have |Im(y)| ≥ π — e.g. 1 - x² with complex x "
            "whose |Im(x²)| can hit ~8 on complex-box. The K=11 `sub` witness "
            "suffices when y stays inside the principal strip |Im(y)| < π."
        ),
        paper_k=None,
        proof_engine_k=None,
        verdict="upper-bound",
    ),
    "asin_complex_box": Witness(
        name="asin_complex_box",
        arity=1,
        K=429,
        depth=52,
        minimal=False,
        proof_url=None,
        tree="eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1)), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1)), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, 1), 1))",
        note=(
            "complex-box-honest asin = -i · ln(i·x + sqrt(1-x)·sqrt(1+x)); "
            "i-cascade 2026-04-19 shrank this witness from K=461 → K=429 "
            "(delta -32) by substituting the new K=75 i subtree "
            "(sqrt(neg(1))) for the old K=91 9-stage i in its two "
            "occurrences. Now 1.27× the K=305 natural-domain asin "
            "(previously 1.37× the K=337 version — both reflect the same "
            "i-cascade). Equivalence max_diff ~1.1e-14 on unit-disk-interior "
            "and ~2.9e-14 on complex-box (samples=4096, tolerance=1e-10). "
            "Branch probes on real-axis-outside-[-1,1] all pass (8/8, "
            "max_diff ~1.1e-14). Uses add_complex_box for the sum inside the "
            "log (|Im| of iz + sqrt(1-x²) can exceed π on complex-box) and "
            "factors sqrt(1-x²) = sqrt(1-x)·sqrt(1+x) to avoid feeding a "
            "large-|Im| argument to the log-exp-based sub witness. "
            "sub_complex_box handles 1-x via add_complex_box(1, neg(x))."
        ),
        paper_k=None,
        proof_engine_k=None,
        verdict="upper-bound",
    ),
    "acos_complex_box": Witness(
        name="acos_complex_box",
        arity=1,
        K=429,
        depth=56,
        minimal=False,
        proof_url=None,
        tree="eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, x), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1)), 1)), 1)), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, 1), 1))",
        note=(
            "complex-box-honest acos = -i · ln(x + i · sqrt(1-x)·sqrt(1+x)); "
            "i-cascade 2026-04-19 shrank this witness from K=461 → K=429 "
            "(delta -32) by substituting the new K=75 i subtree "
            "(sqrt(neg(1))) for the old K=91 9-stage i in its two "
            "occurrences. Now 0.88× the K=485 π/2−asin textbook path "
            "(previously 0.87× the K=533 version — the mult+pi surcharge in "
            "the textbook path outweighs the direct -i·ln(...) construction "
            "on both sides of the cascade). Equivalence max_diff ~2.0e-14 on "
            "unit-disk-interior, ~2.4e-14 on complex-box (samples=4096, "
            "tolerance=1e-10). Branch probes on real-axis-outside-[-1,1] all "
            "pass (8/8, max_diff ~2.0e-14). Same sqrt factorization and "
            "add_complex_box composition as asin_complex_box."
        ),
        paper_k=None,
        proof_engine_k=None,
        verdict="upper-bound",
    ),
    "atan_complex_box": Witness(
        name="atan_complex_box",
        arity=1,
        K=355,
        depth=40,
        minimal=False,
        proof_url=None,
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), eml(x, 1)))), 1)), eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1)), 1)), 1))), 1)), 1)",
        note=(
            "complex-box-honest atan = (i/2) · ln((i+x)/(i-x)); i-cascade "
            "2026-04-19 shrank this witness from K=403 → K=355 (delta -48) "
            "by substituting the new K=75 i subtree (sqrt(neg(1))) for the "
            "old K=91 9-stage i in its three occurrences. Still same K as "
            "the natural-domain atan (355) — the only branch-cut-unsafe "
            "subtree in the original was the K=19 `add` for (i+x), which "
            "add_complex_box (K=27) replaces; the K=11 sub for (i-x) is "
            "retained because |Im(i-x)| ≤ 3 < π stays inside sub's "
            "principal strip on complex-box. Equivalence max_diff ~1.3e-15 "
            "on real-interval, ~3.5e-14 on complex-box (samples=4096, "
            "tolerance=1e-10). Branch probes on imag-axis-outside-[-i,i] all "
            "pass (8/8, max_diff ~1.3e-15)."
        ),
        paper_k=None,
        proof_engine_k=None,
        verdict="upper-bound",
    ),
})

# --- log_x_y harvest: binary base-x logarithm, composed from ln + sub ---
# Identity: log_x(y) = ln(y)/ln(x) = exp(ln(ln(y)) - ln(ln(x))), encoded as
# eml(sub(ln(ln(y)), ln(ln(x))), 1) — the outer eml(·, 1) evaluates exp of its
# first argument because log(1)=0. Paper Table 4 publishes compiler K=117 and
# direct-search K=29 for log_x(y) — our K=37 beats the compiler by 80 tokens
# but sits 8 above the direct-search floor (which is a search bound, not
# library composition). The brief's composition arithmetic assumed K(div)=17,
# but our div witness is K=33; div-based paths land at K=45. The
# exp(sub(ln·ln(y),ln·ln(x))) encoding is the shortest library composition at
# K=37. Closing the K=37 → K=29 gap is a future search target.
WITNESSES.update({
    "log_x_y": Witness(
        name="log_x_y", arity=2, K=37, depth=11, minimal=False,
        proof_url=None,  # not published standalone; composed from ln + sub
        tree=(
            "eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(1, "
            "eml(eml(1, y), 1))), 1))), 1)), eml(eml(1, eml(eml(1, "
            "eml(1, eml(eml(1, x), 1))), 1)), 1)), 1)"
        ),
        note=(
            "log_x(y) = ln(y)/ln(x) encoded as exp(ln(ln(y))-ln(ln(x))) via "
            "eml(sub(ln(ln(y)), ln(ln(x))), 1). K=37 beats paper Table 4 "
            "compiler K=117 by 80; 8 above direct-search K=29. Equivalence "
            "max_diff < 1e-12 on right-half-plane; positive-reals degrades "
            "near x=1 (log(x)→0 amplifies round-off) but still < 1e-10 on "
            "typical seeds. Safe domain: right-half-plane."
        ),
        paper_k=29, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="direct-search",
        paper_k_direct=29,
        paper_k_direct_lower=None,
    ),
})

# --- specialized unary harvest (arXiv:2603.21852 Table 4 direct-search rows) ---
# Five primitives are compile-time compositions of existing witnesses, but the
# paper publishes direct-search K values separately from its compiler K.
# Storing them lets the compiler route `x**2 → sq`, `x+1 → succ`, etc.
# instead of re-composing the general forms. Four match paper direct-search
# K exactly; `half` (paper K=27) is not reachable from compile-time
# composition — beam search (max_k=27, per_level_cap=100k, seed-witnesses,
# 90s budget) enumerated 467k candidates without a hit.
WITNESSES.update({
    "sq": Witness(
        name="sq", arity=1, K=17, depth=8, minimal=False, proof_url=None,
        tree="eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1)",
        note=(
            "sq(x) = mult(x, x); substitute y->x in the K=17 mult witness. K=17 "
            "matches paper Table 4 direct-search K=17 exactly. Equivalence "
            "max_diff < 1e-14 on complex-box."
        ),
        paper_k=17, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="direct-search",
        paper_k_direct=17,
    ),
    "succ": Witness(
        name="succ", arity=1, K=19, depth=8, minimal=False, proof_url=None,
        tree="eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(1, 1)), 1))",
        note=(
            "succ(x) = add(x, 1); substitute y->1 in the K=19 add witness. "
            "K=19 matches paper Table 4 direct-search K=19. Equivalence "
            "max_diff < 1e-15 on real-interval."
        ),
        paper_k=19, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="direct-search",
        paper_k_direct=19,
    ),
    "pred": Witness(
        name="pred", arity=1, K=11, depth=4, minimal=False, proof_url=None,
        tree="eml(eml(1, eml(eml(1, x), 1)), eml(1, 1))",
        note=(
            "pred(x) = sub(x, 1); substitute y->1 in the K=11 sub witness. "
            "K=11 matches paper Table 4 direct-search K=11. Equivalence "
            "max_diff < 1e-15 on complex-box."
        ),
        paper_k=11, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="direct-search",
        paper_k_direct=11,
    ),
    "double": Witness(
        name="double", arity=1, K=19, depth=8, minimal=False, proof_url=None,
        tree="eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(x, 1)), 1))",
        note=(
            "double(x) = add(x, x); substitute y->x in the K=19 add witness. "
            "K=19 matches paper Table 4 direct-search K=19. Equivalence "
            "max_diff < 1e-15 on real-interval."
        ),
        paper_k=19, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="direct-search",
        paper_k_direct=19,
    ),
    "half": Witness(
        name="half", arity=1, K=43, depth=14, minimal=False, proof_url=None,
        tree="eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1))), 1)), 1)), 1)",
        note=(
            "half(x) = x/2 built as exp(sub(ln(x), ln(2))) where 2=add(1,1). "
            "K=43 is an upper bound: beam search (max_k=27, per_level_cap=100k, "
            "seed-witnesses, 90s) enumerated 467k candidates without reaching "
            "paper Table 4 direct-search K=27. Retry 2026-04-19 at "
            "per_level_cap=200k, time_budget=1800s, seed-witnesses + "
            "seed-subtrees: 1.27M candidates over 1810s, cap saturated at "
            "K=17..K=27 (200k each), still no hit (see docs/half-k27-null-"
            "2026-04-19.md). Naive div(x, add(1,1)) and mult(x, inv(add(1,1))) "
            "both give K=51; the ln/sub/exp composition saves 8 tokens. "
            "Equivalence max_diff < 1e-14 on right-half-plane."
        ),
        paper_k=27, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="direct-search",
        paper_k_direct=27,
    ),
})


# --- Table-4 constants harvest (2026-04-19): IEEE-feasible arity-0 rows ---
# Source: `docs/paper-table4-coverage-audit-2026-04-19.md`. Each entry is a
# trivial substitution off an existing witness (append-only; no new search).
# K values match the audit's "our K" column and were re-verified via
# k_tokens(parse(tree)) before shipping. All four trees evaluate (via cmath
# principal-branch `evaluate`) to the intended constant within 1e-14.
#
# Verdicts and Table-4 column mapping:
#   zero       K=7   — direct-search K=7 (both columns equal); minimal per paper.
#   minus_one  K=17  — direct-search K=15 uses extended reals; non-ext column
#                      (17) matches ours exactly. IEEE-feasible path is K=17.
#   two        K=19  — direct-search K=19; matches paper exact.
#   half       K=35  — direct-search K=29 uses extended reals; non-ext column
#                      (35) matches ours exactly.
# Every row cites Table 4 compiler K, direct-search K, and the composition path
# in its `note` per the harvest protocol.
WITNESSES.update({
    "zero": Witness(
        name="zero", arity=0, K=7, depth=3, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-triple-nesting-recovers-ln-x/",
        tree="eml(1, eml(eml(1, 1), 1))",
        note=(
            "Table 4 constant `0`: paper compiler K=7, paper direct-search K=7 (both "
            "columns equal — matches paper's minimum exactly). Composition path: "
            "`ln(1)` = substitute x=1 in the K=7 ln witness. Verified via "
            "evaluate(parse(tree), 0, 0) = 0+0j exactly. Append-only harvest from "
            "`docs/paper-table4-coverage-audit-2026-04-19.md`."
        ),
        paper_k=7, proof_engine_k=None, verdict="minimal",
        paper_k_source="direct-search", paper_k_direct=7, paper_k_direct_lower=None,
    ),
    "minus_one": Witness(
        name="minus_one", arity=0, K=17, depth=6, minimal=True,
        proof_url=None,
        tree="eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))",
        note=(
            "Table 4 constant `-1`: paper compiler K=17, paper direct-search K=15 "
            "(extended-reals) / K=17 (non-extended, parenthesised column). Our K=17 "
            "matches the IEEE non-extended column exactly; paper's K=15 uses "
            "log(0)=-inf and is not reproducible under principal-branch cmath (see "
            "`project_neg_inv_k15_extended_reals.md`). Composition path: `neg(1)` = "
            "substitute x=1 in the K=17 neg witness. Verified via "
            "evaluate(parse(tree), 0, 0) ≈ -1 within 1e-14. "
            "**Minimality proof-by-exhaustion (2026-04-19)**: exhaustive enumeration "
            "of every arity-0 leaf-only EML tree at K in {1,3,5,7,9,11,13,15} "
            "(Catalan totals 1+1+2+5+14+42+132+429 = 626 syntactic trees; 355 "
            "unique function values under cmath principal-branch semantics) found "
            "NO tree within 1e-10 of -1+0j. IEEE-feasible minimum is therefore "
            "K=17, matching the paper's non-extended direct-search column exactly. "
            "See `docs/minus-one-k17-minimality-proof-2026-04-19.md` and "
            "`eml-skill/scripts/minus_one_exhaustive.py`."
        ),
        paper_k=17, proof_engine_k=None, verdict="minimal",
        paper_k_source="direct-search", paper_k_direct=17, paper_k_direct_lower=None,
    ),
    "two": Witness(
        name="two", arity=0, K=19, depth=8, minimal=False,
        proof_url="https://yaniv-golan.github.io/proof-engine/proofs/eml-k19-addition-tree/",
        tree="eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1))",
        note=(
            "Table 4 constant `2`: paper compiler K=27, paper direct-search K=19 "
            "(both columns equal — matches paper's minimum exactly). Composition "
            "path: `add(1, 1)` = substitute x=1, y=1 in the K=19 add witness. "
            "Verified via evaluate(parse(tree), 0, 0) ≈ 2 within 1e-14. Unlocks "
            "cleaner K accounting for downstream rows (x/2, 2x, sqrt(2), 1/2)."
        ),
        paper_k=27, proof_engine_k=None, verdict="minimal",
        paper_k_source="direct-search", paper_k_direct=19, paper_k_direct_lower=None,
    ),
    "half_const": Witness(
        name="half_const", arity=0, K=35, depth=14, minimal=False,
        proof_url=None,
        tree="eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)",
        note=(
            "Table 4 constant `1/2`: paper compiler K=91, paper direct-search K=29 "
            "(extended-reals) / K=35 (non-extended, parenthesised column). Our K=35 "
            "matches the IEEE non-extended column exactly; paper's K=29 requires "
            "extended-reals semantics unavailable under principal-branch cmath. "
            "Composition path: `inv(two)` = substitute x=two-tree in the K=17 inv "
            "witness (35 = 17 + (19-1)·1). Verified via evaluate(parse(tree), 0, 0) "
            "≈ 0.5 within 1e-14. Renamed from `half` to avoid collision with the "
            "specialized-unary witness `half(x) = x/2` (K=43, arity=1)."
        ),
        paper_k=91, proof_engine_k=None, verdict="upper-bound",
        paper_k_source="direct-search", paper_k_direct=35, paper_k_direct_lower=None,
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
