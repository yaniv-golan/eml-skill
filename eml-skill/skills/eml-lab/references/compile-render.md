# `compile-render` reference

The `compile-render` subcommand is the one-shot artifact builder. Read this
when the caller needs to understand the output bundle, the auto-domain
algorithm, or the Mermaid fallback rules.

## Output bundle

Every `compile-render --out-dir DIR` run writes these files into `DIR`:

| file          | content |
|---------------|---------|
| `tree.txt`    | Nested form and RPN of the lowered EML tree. |
| `diagram.md`  | Mermaid diagram (or fenced RPN text block for K > 500). |
| `diagram.svg` | Graphviz-rendered SVG (only when `--render svg` and `dot` is on PATH). |
| `audit.json`  | Structured audit report: shape stats, `sympy.lambdify` comparison, domain, samples, branch flags. |
| `audit.md`    | Markdown rendering of `audit.json`. |
| `summary.md`  | Human-readable one-pager stitching lowered form + K + audit verdict + caveats. |

The audit is a numerical sanity check against
`sympy.lambdify(..., modules='cmath')` — it catches compile-time mistakes,
not principal-branch subtleties. For a branch-aware verdict chain the output
through `/eml-check`.

## Auto-domain algorithm

When `--domain` is omitted, `compile-render` picks the narrowest named
domain that every witness in the lowered tree supports. Narrowing priority,
narrowest first:

1. `positive-reals` — chosen whenever any of `add`, `sub`, `mult`, `ln`,
   `sqrt`, `log10`, `asin`, `acos` appears.
2. `unit-disk-interior` — chosen when the tree needs an open disk around
   the origin but no half-plane restriction.
3. `complex-box` — the default fallback; every primitive evaluates there.

The chosen domain prints on stderr as `# auto-domain: <name>` so downstream
scripts can inspect or override. Pass `--domain complex-box` explicitly to
disable narrowing (useful when stressing branch-cut coverage on a tree that
would otherwise run on `positive-reals`).

## Mermaid fallback for large trees

`to_mermaid_doc` emits a Mermaid flowchart by default, but GitHub's inline
Mermaid renderer grays out on large diagrams. When the tree exceeds
`mermaid_max_nodes=500`, `diagram.md` falls back to a fenced `text` block
containing the RPN form. This keeps the document readable on GitHub
without producing a silently broken diagram. Override the threshold with
`--mermaid-max-nodes N`.

## K-faithfulness vs K-minimality

`compile-render` is faithful to the shipped witness library — it never
shortens trees. The flagship example `sin(sqrt(x) + cos(x))` lowers to
K=1151 via straight library substitution. Run `/eml-optimize search` on
subtrees if you need a smaller artifact.
