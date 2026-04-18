# `/eml-check` audit report schema (v1)

The audit CLI writes `audit.json` (this schema) and `audit.md` (human-friendly
rendering) into `--out-dir`. Schema version pins behavior per field; bump the
`schema_version` string only when a consumer-visible field changes semantics.

## Top-level fields

| field            | type                          | required | description                                                              |
|------------------|-------------------------------|----------|--------------------------------------------------------------------------|
| `schema_version` | string                        | yes      | Currently `"1"`.                                                         |
| `verdict`        | enum                          | yes      | `verified`, `verified-with-caveats`, `numerical-mismatch`, `shape-invalid`. |
| `tree`           | string                        | yes      | Echoed input tree (nested, RPN, or JSON — as-given, unnormalised).       |
| `claim`          | string                        | yes      | Echoed claim name (e.g. `exp`, `ln`, `mult`).                            |
| `shape`          | object                        | yes      | See below.                                                               |
| `numerical`      | object                        | yes      | See below.                                                               |
| `branch_flags`   | list[object]                  | yes      | May be empty. See below.                                                 |
| `caveats`        | list[string]                  | yes      | Freeform human-readable notes that shaped the verdict.                   |
| `worst_cases`    | list[object]                  | yes      | Capped at 10. See below.                                                 |

## `shape`

```json
{"K": 3, "depth": 1, "leaves": {"1": 1, "x": 1, "y": 0}}
```

- `K` — RPN token count (leaves + operator nodes).
- `depth` — longest root-to-leaf edge count.
- `leaves` — per-symbol leaf counts. Missing keys are `0`. The leaf alphabet is
  fixed at `{1, x, y}`; any other symbol triggers `shape-invalid` at parse
  time, which short-circuits the rest of the report.

## `numerical`

```json
{"domain": "complex-box", "samples": 70, "tolerance": 1e-10, "max_abs_diff": 0.0}
```

- `domain` — named interior domain (`positive-reals`, `real-interval`,
  `complex-box`, `unit-disk-interior`, `right-half-plane`) or `n/a` when the
  tree failed to parse.
- `samples` — number of interior points drawn with the given seed.
- `tolerance` — threshold for `max_abs_diff` to still count as `verified`.
- `max_abs_diff` — `max |tree(x,y) − reference(x,y)|` across samples; may be
  `null` when not evaluated, or the string `"inf"` / `"nan"` for samples the
  evaluator rejected (log of zero, overflow, etc.). Strings are used because
  JSON has no literal for non-finite floats.

## `branch_flags`

Each probe point sits on (or near) a known cut of the claim's reference
function. Entries are straddle pairs at `±iε` around the cut.

```json
{"locus": "neg-real-axis", "sample": "(-1+1e-06j)", "abs_diff": 0.0}
```

- `locus` — `neg-real-axis`, `real-axis-outside-[-1,1]`,
  `imag-axis-outside-[-i,i]`, or empty list for entire functions.
- `sample` — formatted complex string.
- `abs_diff` — numeric, or `"nan"` when the evaluator threw.

If `abs_diff > tolerance`, a `caveats` entry is appended with the locus/sample
and the verdict decays to `verified-with-caveats` (or stays
`numerical-mismatch` if the bulk sampler also failed).

## `worst_cases`

Worst offenders from the bulk sample sweep, trimmed to 10 entries, sorted by
decreasing `abs_diff` in most sessions but not guaranteed — read it as "up to
10 examples the auditor picked, not a ranked list".

```json
{"x": "(0.5+0j)", "y": "(1+0j)",
 "tree_value": "(1.648+0j)", "ref_value": "(1.649+0j)", "abs_diff": 1.2e-03}
```

## Verdict decision tree

1. Parse fails or tree uses a leaf outside `{1, x, y}` → `shape-invalid`, exit 2.
2. Bulk `max_abs_diff > tolerance` → `numerical-mismatch`, exit 1.
3. Otherwise with at least one caveat (branch mismatch, unary/y note, etc.)
   → `verified-with-caveats`, exit 0.
4. Otherwise → `verified`, exit 0.

Usage errors (unknown claim, unknown domain) exit 3 and do not produce a report.

## Canonical-representative drift

The minimality auditor (`skills/_shared/eml_core/minimality.py`) enumerates
trees bottom-up and deduplicates by a hash over sampled values, keeping one
canonical representative per unique function at each K. The choice of combine
kernel (cmath vs. numpy) and rounding mode (python `round` vs. `np.round`)
determines **which** representative wins a hash bucket, and those bit-level
differences propagate when the bucket's representative is combined at K+1,
K+2, … — so enumerator configuration can change whether a given function
surfaces at a given K.

Investigation matrix for K=17 unary `neg`:

| combine | hash         | K=17 unary neg outcome |
|---------|--------------|------------------------|
| cmath   | python round | null (67s)             |
| cmath   | np.round     | found (15.8s)          |
| numpy   | python round | found (49.4s)          |
| numpy   | np.round     | **found (6.9s)** ← shipped |

Consequence for the audit contract: a `not found at K ≤ K*` result is
exhaustive **modulo the canonical-representative choice** (enumerator kernel
+ rounding mode), not over the full tree space. Any `found_at_k=K` result is
independently verifiable — `audit.py` re-checks the reported witness via the
standard numerical + branch-cut pipeline, which does not depend on the
enumerator's hash bucketing.

In practice this is a non-issue at K ≤ 13 (pin-verified against the analytic
syntactic recurrence) and produces only additive discoveries at K ≥ 15.

## Blog format (`--format blog`)

A third emitter alongside `to_json` / `to_markdown`:
`AuditReport.to_blog(witness, repo_url, tool_version)` → presentation-only
markdown intended for pasting into a README, gist, or Substack post. It is
**not part of the v1 consumer contract** — fields and section labels may
shift between minor versions. The CLI writes it as `audit.blog.md`.

Sections, in order:

1. **Title + verdict badge.** `# {emoji} \`{claim}\` — {label}`. Emoji is
   ✅ when `witness.minimal=True`, 🔴 when the witness's note contains
   `"not reproducible"` (i.e. an upward-refuted paper claim like `neg`/`inv`),
   and 🟡 otherwise. Unknown claims (no library entry) fall back to a verdict-
   derived badge.
2. **Audit-verdict line.** Echoes the `verdict`, `max_abs_diff`, domain,
   sample count, and tolerance from the v1 fields.
3. **Tree section.** Embedded Mermaid `graph TD` rendering for K ≤ 30 nodes;
   RPN string in a fenced code block above that cap (constant
   `BLOG_INLINE_NODE_CAP = 30` in `schemas.py`).
4. **K-context table.** Three rows: our `WITNESSES` K (with a minimality
   note), paper Table 4 (always `—` because that file is markdown, not
   machine-readable), and proof-engine (always `—`; the URL is rendered in
   provenance instead). Mark anything missing as `—`; do not fabricate.
5. **Provenance.** `proof_url` rendered as a markdown link, plus the
   library `note` field as a blockquote. For witnesses without a
   `proof_url` (e.g. beam-discovered `neg`/`inv`) the row says so explicitly.
6. **Branch-cut probes.** Table with columns `locus`, `sample`,
   `max |diff|`, `passed` (✅/❌/skipped). Trailing line counts skipped
   probes (NaN abs_diff = "evaluator threw at the boundary"). Empty case
   prints a one-liner that the claim is treated as entire on the sampled
   domain. A trailing blockquote surfaces the upstream-domain caveat for
   witnesses whose note flags an ADD-witness limitation.
7. **Audit caveats.** Pass-through of `report.caveats`.
8. **Footer.** `eml-check vX.Y --format blog · ISO timestamp · repo link`.
   The `--repo-url` flag injects the URL; default is the literal
   `<REPO_URL>` placeholder for downstream substitution.

The blog format is **read-only output** — it never executes anything beyond
the existing audit pipeline. It re-uses `schema_version=1` fields exclusively;
no new audit data is collected.

## Consumer contract

Downstream tools (graders, eval viewer) may rely on:

- `schema_version == "1"`
- `verdict` being one of the four enumerated strings
- `shape.K`, `shape.depth`, `shape.leaves.{1,x,y}` always present
- `numerical.max_abs_diff` being numeric or one of `null`, `"inf"`, `"nan"`

Everything else (exact locus labels, `sample` formatting, worst-case ordering)
is best-effort and may shift in a minor version.
