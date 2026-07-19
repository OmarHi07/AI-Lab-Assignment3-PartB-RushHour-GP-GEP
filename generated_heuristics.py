"""Load saved GP/GEP expressions as heuristics for the Assignment 1 A*."""

import json
from pathlib import Path

from evolution_common import ExpressionNode, make_heuristic


def load_evolved_heuristic(json_path):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    expression = ExpressionNode.from_dict(data["tree"])
    heuristic = make_heuristic(expression)
    heuristic.__name__ = f"{data['method'].lower()}_generated_heuristic"
    return heuristic


def load_best_generated(output_directory="outputs"):
    output_directory = Path(output_directory)
    loaded = {}
    for method in ("gp", "gep"):
        path = output_directory / f"best_{method}_heuristic.json"
        if path.exists():
            loaded[method.upper()] = load_evolved_heuristic(path)
    return loaded
