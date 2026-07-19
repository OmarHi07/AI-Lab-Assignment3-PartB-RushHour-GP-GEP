import unittest
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from evolution_common import ExpressionNode, apply_function, make_heuristic
from features import TERMINAL_NAMES, extract_features
from gep_engine import decode_chromosome, tail_length
from generated_heuristics import load_best_generated
from heuristics import h5
from fitness import DEFAULT_TRAIN_IDS, DEFAULT_VALIDATION_IDS
from main import apply_solution, format_solution, print_all_solutions
from parser import load_puzzles
from search import astar, is_goal
from reporting import summarize_benchmarks
from run_part_b import validate_problem_split


class PartBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.puzzles = load_puzzles("rh.txt")

    def test_required_solution_format(self):
        internal = ["3CL", "3OD", "4AR", "1PU", "1BU", "2RL", "2QD", "3XR"]
        self.assertEqual(
            format_solution(internal),
            "CL3 OD3 AR4 PU1 BU1 RL2 QD2 XR3",
        )

    def test_solution_printer_uses_required_label_and_period(self):
        result = astar(self.puzzles[0], h5, time_limit_seconds=2)
        result.update(
            {"problem": 1, "algorithm": "A*", "heuristic_name": "h5"}
        )
        output = StringIO()
        with redirect_stdout(output):
            print_all_solutions([result], self.puzzles, show_final_board=False)
        printed = output.getvalue()
        self.assertIn("Soln: ", printed)
        self.assertIn(" .", printed)
        self.assertNotIn("Final board:", printed)

    def test_first_puzzle_h5_solution_is_legal(self):
        result = astar(self.puzzles[0], h5, time_limit_seconds=2)
        self.assertTrue(result["success"])
        final_state = apply_solution(self.puzzles[0], result["solution"])
        self.assertTrue(is_goal(final_state))

    def test_astar_node_budget(self):
        result = astar(
            self.puzzles[0], h5, time_limit_seconds=2, node_limit=1
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["termination_reason"], "node_limit")
        self.assertEqual(result["nodes_expanded"], 1)

    def test_final_split_is_balanced_24_8_8(self):
        validate_problem_split(DEFAULT_TRAIN_IDS, DEFAULT_VALIDATION_IDS, 40)
        test_ids = set(range(1, 41)) - set(DEFAULT_TRAIN_IDS) - set(
            DEFAULT_VALIDATION_IDS
        )
        self.assertEqual(len(DEFAULT_TRAIN_IDS), 24)
        self.assertEqual(len(DEFAULT_VALIDATION_IDS), 8)
        self.assertEqual(len(test_ids), 8)
        for group_start in (1, 11, 21, 31):
            group = set(range(group_start, group_start + 10))
            self.assertEqual(len(group & set(DEFAULT_TRAIN_IDS)), 6)
            self.assertEqual(len(group & set(DEFAULT_VALIDATION_IDS)), 2)
            self.assertEqual(len(group & test_ids), 2)

    def test_success_rate_has_priority_in_final_ranking(self):
        common = {
            "method": "test",
            "solution_length": 1,
            "optimal_length": 1,
            "solution_gap": 0.0,
            "nodes_generated": 1,
            "heuristic_evaluations": 1,
            "runtime_seconds_median": 0.01,
            "ebf": 1.0,
            "operator_count": None,
            "tree_depth": None,
            "prefix_expression": None,
            "infix_expression": None,
            "termination_reason": "goal",
        }
        rows = [
            {
                **common,
                "problem": 1,
                "heuristic": "solves_all",
                "success": 1,
                "nodes_expanded": 10_000,
            },
            {
                **common,
                "problem": 1,
                "heuristic": "fails_fast",
                "success": 0,
                "solution_length": None,
                "solution_gap": None,
                "nodes_expanded": 1,
                "termination_reason": "time_limit",
            },
        ]
        summary = summarize_benchmarks(rows)
        self.assertEqual(summary[0]["heuristic"], "solves_all")

    def test_feature_vector_has_all_terminals(self):
        values = extract_features(self.puzzles[0])
        self.assertEqual(tuple(values), TERMINAL_NAMES)
        self.assertEqual(values["D"], 3.0)
        self.assertEqual(values["B"], 2.0)

    def test_protected_division(self):
        self.assertEqual(apply_function("/", [7.0, 0.0]), 0.0)

    def test_generated_heuristic_is_zero_at_goal(self):
        result = astar(self.puzzles[0], h5, time_limit_seconds=2)
        goal = apply_solution(self.puzzles[0], result["solution"])
        expression = ExpressionNode("V")
        self.assertEqual(make_heuristic(expression)(goal), 0.0)

    def test_gep_tail_and_decode(self):
        self.assertEqual(tail_length(8), 9)
        chromosome = ["+", "B", "K"] + ["D"] * 14
        expression = decode_chromosome(chromosome)
        self.assertEqual(expression.prefix(), "(+ B K)")

    def test_saved_generated_heuristics_load_and_solve(self):
        with TemporaryDirectory() as directory:
            for method in ("gp", "gep"):
                payload = {
                    "method": method.upper(),
                    "tree": ExpressionNode("B").to_dict(),
                }
                Path(directory, f"best_{method}_heuristic.json").write_text(
                    json.dumps(payload), encoding="utf-8"
                )
            loaded = load_best_generated(directory)
            self.assertEqual(set(loaded), {"GP", "GEP"})
            for heuristic in loaded.values():
                result = astar(self.puzzles[0], heuristic, time_limit_seconds=2)
                self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
