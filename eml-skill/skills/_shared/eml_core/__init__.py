"""Shared EML core — evaluator, domain samplers, branch-cut probes, reference functions.

Operator: eml(a, b) = cmath.exp(a) - cmath.log(b)
See skills/_shared/eml-foundations.md for axioms, leaf alphabet, branch convention.
"""

from .eml import (
    EmlNode,
    Leaf,
    Node,
    ParseError,
    depth,
    evaluate,
    k_tokens,
    leaf_counts,
    parse,
    to_rpn,
)
from .extended import evaluate_extended, extended_reference

__all__ = [
    "EmlNode",
    "Leaf",
    "Node",
    "ParseError",
    "depth",
    "evaluate",
    "evaluate_extended",
    "extended_reference",
    "k_tokens",
    "leaf_counts",
    "parse",
    "to_rpn",
]
