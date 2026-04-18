"""Tree → JSON AST, Graphviz DOT, Mermaid flowchart."""

from __future__ import annotations

import shutil
import subprocess

from .eml import EmlNode, Leaf, Node, k_tokens, to_rpn


class GraphvizUnavailable(RuntimeError):
    """Raised when the `dot` binary is not on PATH."""


def to_json_ast(ast: Node) -> dict:
    if isinstance(ast, Leaf):
        return {"leaf": ast.symbol}
    return {"eml": [to_json_ast(ast.a), to_json_ast(ast.b)]}


def to_graphviz(ast: Node, title: str = "") -> str:
    lines = ["digraph EML {"]
    lines.append('  node [fontname="Menlo"];')
    if title:
        lines.append(f'  labelloc="t"; label={_dot_str(title)};')
    counter = [0]

    def emit(node: Node) -> int:
        nid = counter[0]
        counter[0] += 1
        if isinstance(node, Leaf):
            lines.append(
                f'  n{nid} [label="{node.symbol}", shape=circle, style=filled, fillcolor="lightblue"];'
            )
        else:
            lines.append(f'  n{nid} [label="eml", shape=box];')
            a_id = emit(node.a)
            b_id = emit(node.b)
            lines.append(f'  n{nid} -> n{a_id} [label="a"];')
            lines.append(f'  n{nid} -> n{b_id} [label="b"];')
        return nid

    emit(ast)
    lines.append("}")
    return "\n".join(lines) + "\n"


def to_mermaid(ast: Node, title: str = "") -> str:
    lines = []
    if title:
        lines.append(f"---")
        lines.append(f"title: {title}")
        lines.append(f"---")
    lines.append("flowchart TD")
    counter = [0]

    def emit(node: Node) -> int:
        nid = counter[0]
        counter[0] += 1
        if isinstance(node, Leaf):
            lines.append(f'  n{nid}(("{node.symbol}"))')
        else:
            lines.append(f"  n{nid}[eml]")
            a_id = emit(node.a)
            b_id = emit(node.b)
            lines.append(f"  n{nid} -->|a| n{a_id}")
            lines.append(f"  n{nid} -->|b| n{b_id}")
        return nid

    emit(ast)
    return "\n".join(lines) + "\n"


def _dot_str(s: str) -> str:
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def to_mermaid_doc(ast: Node, title: str = "", mermaid_max_nodes: int = 500) -> str:
    """Mermaid flowchart wrapped in a fenced markdown code block.

    Renders in GitHub-flavored markdown viewers and on github.com / gists.
    Pairs naturally with summary.md emission.

    When the tree's RPN token count exceeds ``mermaid_max_nodes`` (default 500),
    GitHub's inline Mermaid renderer fails with a gray-box error. In that case,
    emit a fenced ``text`` block containing an explanatory note plus the RPN
    form of the tree, so the markdown stays a single fenced block.
    """
    n_nodes = k_tokens(ast)
    if n_nodes > mermaid_max_nodes:
        note = (
            f"Tree too large for inline Mermaid rendering on GitHub "
            f"(N = {n_nodes} > {mermaid_max_nodes} nodes); RPN form below"
        )
        rpn = to_rpn(ast)
        header = f"{title}\n" if title else ""
        return "```text\n" + header + note + "\n\n" + rpn + "\n```\n"
    body = to_mermaid(ast, title=title)
    return "```mermaid\n" + body + "```\n"


def render_graphviz_svg(ast: Node, title: str = "") -> bytes:
    """Render tree to SVG bytes via the `dot` binary.

    Raises GraphvizUnavailable if `dot` is not on PATH. Callers that want a
    graceful fallback should catch this and suggest `--render mermaid`.
    """
    if shutil.which("dot") is None:
        raise GraphvizUnavailable(
            "graphviz `dot` binary not found on PATH; "
            "install graphviz or use --render mermaid"
        )
    dot_src = to_graphviz(ast, title=title)
    proc = subprocess.run(
        ["dot", "-Tsvg"],
        input=dot_src.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise GraphvizUnavailable(
            f"`dot` exited with {proc.returncode}: "
            f"{proc.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return proc.stdout
