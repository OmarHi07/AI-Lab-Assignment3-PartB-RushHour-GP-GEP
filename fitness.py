"""A* based fitness evaluation shared by GP and GEP."""

from dataclasses import dataclass
from statistics import mean

from evolution_common import make_heuristic
from heuristics import h4, h5
from search import astar, bfs


# Fixed, balanced 24/8/8 split agreed for the final experiment.  The source
# file is ordered in four difficulty groups of ten puzzles.  Each group
# contributes 6 train, 2 validation, and 2 held-out test instances.
DEFAULT_TRAIN_IDS = (
    1, 2, 4, 6, 7, 9,
    11, 12, 14, 16, 17, 19,
    21, 22, 24, 26, 27, 29,
    31, 32, 34, 36, 37, 39,
)
DEFAULT_VALIDATION_IDS = (3, 8, 13, 18, 23, 28, 33, 38)


@dataclass(frozen=True)
class PuzzleBenchmark:
    problem: int
    state: str
    optimal_length: int
    reference_nodes: int
    reference_time_seconds: float
    reference_name: str


@dataclass
class FitnessEvaluation:
    fitness: float
    loss: float
    success_rate: float
    mean_node_ratio: float
    mean_time_ratio: float
    mean_solution_gap: float
    complexity_ratio: float
    operator_count: int
    details: list

    def summary(self):
        return {
            "fitness": self.fitness,
            "loss": self.loss,
            "success_rate": self.success_rate,
            "mean_node_ratio": self.mean_node_ratio,
            "mean_time_ratio": self.mean_time_ratio,
            "mean_solution_gap": self.mean_solution_gap,
            "complexity_ratio": self.complexity_ratio,
            "operator_count": self.operator_count,
        }


def _best_reference(state, time_limit_seconds, node_limit):
    candidates = []
    for name, heuristic in (("h5", h5), ("h4", h4)):
        result = astar(
            state,
            heuristic,
            time_limit_seconds=time_limit_seconds,
            node_limit=node_limit,
        )
        if result["success"]:
            candidates.append((name, result))

    if not candidates:
        raise RuntimeError("Neither h5 nor h4 solved a selected benchmark puzzle")

    # h5 is the Assignment 1 winner and therefore the primary reference. h4 is
    # retained as a fallback for any puzzle on which h5 reaches the budget.
    return next((item for item in candidates if item[0] == "h5"), candidates[0])


def build_benchmarks(
    puzzles,
    problem_ids,
    time_limit_seconds=5.0,
    node_limit=20_000,
    optimal_time_limit_seconds=5.0,
):
    """Precompute h5/h4 references and BFS optimal depths once."""
    benchmarks = []
    for problem in problem_ids:
        state = puzzles[problem - 1]
        reference_name, reference = _best_reference(
            state, time_limit_seconds, node_limit
        )
        optimal = bfs(state, time_limit_seconds=optimal_time_limit_seconds)
        optimal_length = (
            optimal["solution_length"]
            if optimal["success"]
            else reference["solution_length"]
        )
        benchmarks.append(
            PuzzleBenchmark(
                problem=problem,
                state=state,
                optimal_length=optimal_length,
                reference_nodes=max(1, reference["nodes_expanded"]),
                reference_time_seconds=max(1e-6, reference["time_seconds"]),
                reference_name=reference_name,
            )
        )
    return benchmarks


class FitnessEvaluator:
    """Memoized scalar fitness with a parsimony (complexity) bonus."""

    def __init__(
        self,
        benchmarks,
        time_limit_seconds=2.0,
        node_limit=5_000,
        maximum_operators=31,
    ):
        self.benchmarks = tuple(benchmarks)
        self.time_limit_seconds = time_limit_seconds
        self.node_limit = node_limit
        self.maximum_operators = maximum_operators
        self.cache = {}
        self.actual_evaluations = 0

    def __call__(self, expression):
        key = expression.prefix()
        if key not in self.cache:
            self.cache[key] = self._evaluate(expression)
            self.actual_evaluations += 1
        return self.cache[key]

    def _evaluate(self, expression):
        heuristic = make_heuristic(expression)
        details = []
        solved = 0
        node_ratios = []
        time_ratios = []
        solution_gaps = []

        for benchmark in self.benchmarks:
            result = astar(
                benchmark.state,
                heuristic,
                time_limit_seconds=self.time_limit_seconds,
                node_limit=self.node_limit,
            )
            success = result["success"]
            solved += int(success)

            node_ratio = min(
                5.0, result["nodes_expanded"] / benchmark.reference_nodes
            )
            time_ratio = min(
                5.0,
                result["time_seconds"] / benchmark.reference_time_seconds,
            )

            if success:
                solution_gap = max(
                    0.0,
                    (result["solution_length"] - benchmark.optimal_length)
                    / max(1, benchmark.optimal_length),
                )
            else:
                solution_gap = 1.0

            node_ratios.append(node_ratio)
            time_ratios.append(time_ratio)
            solution_gaps.append(solution_gap)
            details.append(
                {
                    "problem": benchmark.problem,
                    "success": success,
                    "solution_length": result["solution_length"],
                    "optimal_length": benchmark.optimal_length,
                    "nodes_expanded": result["nodes_expanded"],
                    "time_seconds": result["time_seconds"],
                    "termination_reason": result["termination_reason"],
                    "node_ratio": node_ratio,
                    "time_ratio": time_ratio,
                    "solution_gap": solution_gap,
                }
            )

        success_rate = solved / len(self.benchmarks)
        complexity_ratio = min(
            1.0, expression.operator_count() / max(1, self.maximum_operators)
        )
        loss = (
            20.0 * (1.0 - success_rate)
            + 0.50 * mean(node_ratios)
            + 0.20 * mean(time_ratios)
            + 0.20 * mean(solution_gaps)
            + 0.10 * complexity_ratio
        )

        return FitnessEvaluation(
            fitness=1.0 / (1.0 + loss),
            loss=loss,
            success_rate=success_rate,
            mean_node_ratio=mean(node_ratios),
            mean_time_ratio=mean(time_ratios),
            mean_solution_gap=mean(solution_gaps),
            complexity_ratio=complexity_ratio,
            operator_count=expression.operator_count(),
            details=details,
        )
