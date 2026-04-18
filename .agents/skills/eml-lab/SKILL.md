---
name: eml-lab
description: Compile ordinary formulas (exp(x+y), x**y, ln(x*y), sin(x)+cos(x), sqrt(x*y), x/y, asin(x), atan(x), log10(x)) into EML trees, look up calculator-primitive witnesses (exp, ln, add, mult, sub, pow, neg, inv, div, pi, i, sin, cos, tan, sqrt, asin, acos, atan, log10), inspect arbitrary EML trees, or run one-shot compile-render to emit tree + diagram + audit + summary from a sympy expression. Use when a user wants to lower a sympy-parseable expression into the EML IR, ask "how many tokens does the mult witness take?", visualize a tree as Graphviz/Mermaid, convert between nested / RPN / JSON forms, read shape stats (K, depth, leaf histogram), or produce a shareable artifact bundle in one command. Every named elementary primitive has a stored tree; the only `needs_tree` entry is `apex` (the closure proof itself, not a callable primitive).
allowed-tools: Bash, Read, Write, Edit
license: MIT
metadata:
  author: Yaniv Golan
  version: 0.1.0
---

# eml-lab — compile, lookup, and inspect EML trees

Read `../_shared/eml_core/` for the underlying types. This skill is a thin CLI on top of that package. `compile-render` output-bundle schema, auto-domain rules, and Mermaid fallback thresholds live in [`references/compile-render.md`](references/compile-render.md).

## When this skill triggers (and when it doesn't)

**Triggers on:** "compile `sin(x)+cos(x)` into EML", "lower this sympy expression", "how many tokens does the mult witness take?", "render this tree as Mermaid", "look up the `atan` witness", "give me an artifact bundle for `exp(x+y)`".

**Does not trigger on:** verifying a tree against a named claim (use `/eml-check`), searching for a shorter tree (`/eml-optimize`), fitting a law from data (`/eml-fit`), or checking arbitrary elementary identities (`/math-identity-check`).

## Modes

- **Compile** (`--compile EXPR`) — lower a sympy-parseable formula into an EML tree by substituting library witnesses (`e`, `exp`, `ln`, `add`, `mult`, `sub`, `pow`, `neg`, `inv`, `div`, `pi`, `i`, `sin`, `cos`, `tan`, `sqrt`, `asin`, `acos`, `atan`, `log10`).
- **Lookup** (`--lookup NAME`) — fetch a witness; emit metadata (K, depth, minimal flag, proof URL) and tree body if stored.
- **Inspect** (`--tree STR`) — parse any EML tree (nested, RPN, JSON) and emit stats + alternate representations.
- **Compile-render** (`compile-render --expr EXPR --out-dir DIR`) — one-shot stitch: compile → render Mermaid/SVG → audit against `sympy.lambdify(..., modules='cmath')` → emit `tree.txt`, `diagram.md`/`diagram.svg`, `audit.json`, `audit.md`, and `summary.md`. See [`references/compile-render.md`](references/compile-render.md) for the bundle schema.

Compile/lookup/inspect share emits: `stats`, `rpn`, `json`, `graphviz`, `mermaid`, `nested`.

## How to run

All commands below assume `cwd` is the repo root. From an installed plugin's root, drop the leading `eml-skill/`; from this skill's own directory, drop `eml-skill/skills/eml-lab/`.

```bash
# legacy (flag-driven):
python eml-skill/skills/eml-lab/scripts/lab.py \
  ( --compile EXPR | --lookup NAME | --tree "eml(...)" | --list ) \
  [--emit stats,rpn,json,graphviz,mermaid,nested] [--out-dir <path>] [--title "label"]

# one-shot compile-render:
python eml-skill/skills/eml-lab/scripts/lab.py compile-render \
    --expr "sin(sqrt(x) + cos(x))" --out-dir /tmp/demo --domain positive-reals \
    [--render mermaid|svg] [--format md|json|blog] [--samples N] [--seed S] [--tolerance T]
```

Exit codes: `0` OK, `1` lookup-not-found / compile blocked, `2` parse error, `3` usage error.

### Examples

```bash
python eml-skill/skills/eml-lab/scripts/lab.py --list
python eml-skill/skills/eml-lab/scripts/lab.py --compile "x*y"                              # mult, K=17
python eml-skill/skills/eml-lab/scripts/lab.py --lookup exp --emit stats,rpn,graphviz
python eml-skill/skills/eml-lab/scripts/lab.py compile-render --expr "exp(x+y)" --out-dir /tmp/demo
```

## Non-goals

- **Not a minimizer.** `x*y` → K=17 `mult` every time. For shorter trees use `/eml-optimize`.
- **Not a verifier.** Branch-cut + equivalence audits live in `/eml-check`. compile-render's audit is a numerical sanity check, not a proof.
- **Not a fitter.** That's `/eml-fit`.

## Don't reimplement

All logic lives in `skills/_shared/eml_core/` — CLI is a thin wrapper:
`compile.compile_formula`, `parse`, `{k_tokens, depth, leaf_counts, to_rpn}`, `viz.{to_graphviz, to_mermaid, to_mermaid_doc, render_graphviz_svg}`, `witnesses.{lookup, names, WITNESSES}`.

## Gotchas

- **`--list` marks proven-minimal entries with `*`.** Upper-bound entries show `depth=-1` (only K published).
- **`compile` inlines library witnesses.** `x*y` returns K=17 every time; use `/eml-optimize` for shorter trees.
- **Triple-nesting LN uses principal-branch `cmath`.** `/eml-check` audits the `+iπ` branch choice on the negative real axis.
- **RPN is space-tokenized.** The paper's compact form (`x1E`) is display-only.
- **compile-render autodetects `--domain` when omitted** — narrowest named domain that all witnesses support. See [`references/compile-render.md`](references/compile-render.md) for the full priority rules.
- **compile-render is K-faithful, not K-minimal.** Flagship `sin(sqrt(x) + cos(x))` lowers to K=1151; `/eml-optimize search` can often shorten it.
- **Graphviz optional.** `--render svg` needs `dot`; missing binary yields a clean "install graphviz or use --render mermaid" exit, not a crash.
- **Mermaid auto-falls-back to RPN for K > 500.** GitHub grays out large diagrams; see [`references/compile-render.md`](references/compile-render.md) for the threshold.

## Test scenarios

1. `--compile "x*y"` → nested `mult` witness, K=17 (exit 0).
2. `--lookup atan --emit stats,rpn` → K=403, proof URL present (exit 0).
3. `--lookup zzz` → `lookup-not-found` (exit 1).
4. `compile-render --expr "exp(x+y)" --out-dir /tmp/d` → 5 files written to `/tmp/d` (exit 0).
5. `--compile "x + unknown_symbol"` → parse error (exit 2).
