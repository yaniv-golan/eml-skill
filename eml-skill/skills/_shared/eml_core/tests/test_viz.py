"""Viz emitters: shape + round-trip."""

from __future__ import annotations

from eml_core import parse, to_rpn
from eml_core.viz import to_graphviz, to_json_ast, to_mermaid


def _ast():
    return parse("eml(1, eml(eml(1, x), 1))")  # ln witness


def test_json_ast_shape():
    j = to_json_ast(_ast())
    assert "eml" in j
    assert isinstance(j["eml"], list) and len(j["eml"]) == 2


def test_json_ast_roundtrip_via_parse():
    j = to_json_ast(_ast())
    # Re-parse the JSON form and verify RPN matches.
    import json as _json
    ast2 = parse(_json.dumps(j))
    assert to_rpn(ast2) == to_rpn(_ast())


def test_graphviz_is_dot():
    dot = to_graphviz(_ast(), title="ln witness")
    assert dot.startswith("digraph EML {")
    assert dot.rstrip().endswith("}")
    assert "ln witness" in dot
    assert "n0 -> n" in dot


def test_graphviz_escapes_title_quotes():
    dot = to_graphviz(_ast(), title='with "quote"')
    assert '\\"quote\\"' in dot


def test_mermaid_flowchart():
    md = to_mermaid(_ast(), title="ln")
    assert "flowchart TD" in md
    assert "title: ln" in md
    assert "-->|a|" in md and "-->|b|" in md


def test_leaf_only_emits():
    leaf = parse("x")
    assert to_json_ast(leaf) == {"leaf": "x"}
    assert "n0 [label=\"x\"" in to_graphviz(leaf)
    assert 'n0(("x"))' in to_mermaid(leaf)


def test_mermaid_doc_wraps_in_fence():
    from eml_core.viz import to_mermaid_doc

    doc = to_mermaid_doc(_ast(), title="ln")
    assert doc.startswith("```mermaid\n")
    assert doc.rstrip().endswith("```")
    assert "flowchart TD" in doc
    assert "title: ln" in doc


def _big_ast(n_eml: int):
    """Left-spine tree of `n_eml` eml nodes: K = 2*n_eml + 1."""
    expr = "x"
    for _ in range(n_eml):
        expr = f"eml({expr}, 1)"
    return parse(expr)


def test_mermaid_doc_small_tree_still_flowchart():
    from eml_core.viz import to_mermaid_doc

    doc = to_mermaid_doc(_ast(), title="ln", mermaid_max_nodes=500)
    assert "flowchart TD" in doc
    assert doc.startswith("```mermaid\n")


def test_mermaid_doc_large_tree_falls_back_to_rpn():
    from eml_core import k_tokens
    from eml_core.viz import to_mermaid_doc

    # threshold=5 forces a small tree into the fallback path for fast tests
    ast = _ast()
    n = k_tokens(ast)
    doc = to_mermaid_doc(ast, title="ln", mermaid_max_nodes=4)
    assert n > 4
    assert doc.startswith("```text\n")
    assert doc.rstrip().endswith("```")
    assert "Tree too large for inline Mermaid rendering on GitHub" in doc
    assert f"N = {n}" in doc
    assert to_rpn(ast) in doc
    assert "flowchart" not in doc
    assert "graph TD" not in doc


def test_mermaid_doc_default_threshold_is_500():
    from eml_core import k_tokens
    from eml_core.viz import to_mermaid_doc

    big = _big_ast(260)  # K = 521 > 500
    assert k_tokens(big) > 500
    doc = to_mermaid_doc(big, title="big")
    assert doc.startswith("```text\n")
    assert "flowchart" not in doc
    assert to_rpn(big) in doc


def test_render_graphviz_svg_missing_binary_raises(monkeypatch):
    import eml_core.viz as vz
    from eml_core.viz import GraphvizUnavailable, render_graphviz_svg

    monkeypatch.setattr(vz.shutil, "which", lambda *_: None)
    import pytest
    with pytest.raises(GraphvizUnavailable):
        render_graphviz_svg(_ast(), title="ln")
