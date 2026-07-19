"""CSV, JSON, ranking, and plot helpers for the Part B report."""

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from stats import compute_ebf


def _write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = fieldnames or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def combine_seed_histories(seed_results):
    """Flatten ``[(seed, evolution_result), ...]`` for CSVs and plots."""
    return [
        {"seed": seed, **row}
        for seed, result in seed_results
        for row in result.history
    ]


def save_history(method, history, output_directory):
    rows = [{"method": method, **row} for row in history]
    _write_csv(Path(output_directory) / f"{method.lower()}_history.csv", rows)


def save_seed_summary(method, rows, output_directory):
    _write_csv(
        Path(output_directory) / f"{method.lower()}_seed_summary.csv",
        [{"method": method, **row} for row in rows],
    )


def save_multi_seed_test_tables(rows, summary, output_directory):
    output_directory = Path(output_directory)
    _write_csv(output_directory / "multi_seed_test_results_by_puzzle.csv", rows)
    _write_csv(output_directory / "multi_seed_test_summary.csv", summary)


def save_evolved_model(
    method,
    expression,
    evaluation,
    output_directory,
    evolution_seconds,
    chromosome=None,
    extra=None,
):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    data = {
        "method": method,
        "prefix": expression.prefix(),
        "infix": expression.infix(),
        "tree": expression.to_dict(),
        "node_count": expression.node_count(),
        "operator_count": expression.operator_count(),
        "depth": expression.depth(),
        "fitness": evaluation.summary(),
        "evolution_time_seconds": evolution_seconds,
    }
    if chromosome is not None:
        data["chromosome"] = chromosome
    if extra:
        data.update(extra)
    path = output_directory / f"best_{method.lower()}_heuristic.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def benchmark_heuristics(
    puzzles,
    heuristic_specs,
    astar_function,
    problem_ids,
    optimal_lengths,
    time_limit_seconds=5.0,
    node_limit=20_000,
    timing_repetitions=3,
    problem_splits=None,
):
    """Evaluate baselines and evolved heuristics under identical budgets."""
    rows = []
    for problem in problem_ids:
        state = puzzles[problem - 1]
        for name, spec in heuristic_specs.items():
            repetitions = [
                astar_function(
                    state,
                    spec["function"],
                    time_limit_seconds=time_limit_seconds,
                    node_limit=node_limit,
                )
                for _ in range(timing_repetitions)
            ]
            result = repetitions[0]
            time_seconds = median(item["time_seconds"] for item in repetitions)
            optimal = optimal_lengths.get(problem)
            gap = None
            if result["success"] and optimal is not None:
                gap = max(0.0, (result["solution_length"] - optimal) / max(1, optimal))
            rows.append(
                {
                    "problem": problem,
                    "split": (problem_splits or {}).get(problem, "all"),
                    "heuristic": name,
                    "method": spec.get("method", "baseline"),
                    "seed": spec.get("seed"),
                    "success": int(result["success"]),
                    "solution_length": result["solution_length"],
                    "optimal_length": optimal,
                    "solution_gap": gap,
                    "nodes_expanded": result["nodes_expanded"],
                    "nodes_generated": result["nodes_generated"],
                    "heuristic_evaluations": result["heuristic_evaluations"],
                    "time_limit_seconds": time_limit_seconds,
                    "node_limit": node_limit,
                    "runtime_seconds_median": time_seconds,
                    "ebf": compute_ebf(
                        result["nodes_expanded"], result["solution_length"]
                    ),
                    "operator_count": spec.get("operator_count"),
                    "tree_depth": spec.get("tree_depth"),
                    "prefix_expression": spec.get("prefix"),
                    "infix_expression": spec.get("infix"),
                    "termination_reason": result["termination_reason"],
                }
            )
    return rows


def summarize_benchmarks(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["heuristic"]].append(row)

    summary = []
    for heuristic, items in grouped.items():
        solved = [item for item in items if item["success"]]
        gaps = [item["solution_gap"] for item in solved if item["solution_gap"] is not None]
        optimal_solutions = sum(gap == 0.0 for gap in gaps)
        summary.append(
            {
                "heuristic": heuristic,
                "method": items[0]["method"],
                "seed": items[0].get("seed"),
                "solved": len(solved),
                "total_puzzles": len(items),
                "success_rate": len(solved) / len(items),
                "time_limit_failures": sum(
                    item["termination_reason"] == "time_limit" for item in items
                ),
                "node_limit_failures": sum(
                    item["termination_reason"] == "node_limit" for item in items
                ),
                "optimal_solutions": optimal_solutions,
                "optimal_rate_among_solved": (
                    optimal_solutions / len(gaps) if gaps else None
                ),
                "mean_solution_gap": mean(gaps) if gaps else None,
                "mean_nodes_expanded": mean(item["nodes_expanded"] for item in items),
                "mean_runtime_seconds": mean(
                    item["runtime_seconds_median"] for item in items
                ),
                "median_runtime_seconds": median(
                    item["runtime_seconds_median"] for item in items
                ),
                "operator_count": items[0]["operator_count"],
                "tree_depth": items[0]["tree_depth"],
                "prefix_expression": items[0]["prefix_expression"],
                "infix_expression": items[0]["infix_expression"],
            }
        )

    def assign_rank(field, key):
        ordered = sorted(range(len(summary)), key=lambda index: key(summary[index]))
        previous_value = object()
        current_rank = 0
        for position, index in enumerate(ordered, start=1):
            value = key(summary[index])
            if value != previous_value:
                current_rank = position
                previous_value = value
            summary[index][field] = current_rank

    assign_rank(
        "quality_rank",
        lambda row: (
            -row["success_rate"],
            row["mean_solution_gap"]
            if row["mean_solution_gap"] is not None
            else 999,
        ),
    )
    assign_rank(
        "node_efficiency_rank",
        lambda row: (-row["success_rate"], row["mean_nodes_expanded"]),
    )
    assign_rank(
        "runtime_rank",
        lambda row: (-row["success_rate"], row["median_runtime_seconds"]),
    )

    generated = [row for row in summary if row["operator_count"] is not None]
    for row in summary:
        row["complexity_rank"] = None
        row["generated_rank"] = None
    for rank, row in enumerate(
        sorted(generated, key=lambda item: item["operator_count"]), start=1
    ):
        row["complexity_rank"] = rank

    best_nodes = min(row["mean_nodes_expanded"] for row in summary)
    best_runtime = min(row["median_runtime_seconds"] for row in summary)
    for row in summary:
        gap = row["mean_solution_gap"] if row["mean_solution_gap"] is not None else 1.0
        quality_score = 1.0 / (1.0 + gap)
        node_score = best_nodes / max(1e-12, row["mean_nodes_expanded"])
        runtime_score = best_runtime / max(1e-12, row["median_runtime_seconds"])
        row["performance_score"] = (
            0.40 * row["success_rate"]
            + 0.25 * quality_score
            + 0.20 * node_score
            + 0.15 * runtime_score
        )

    # The lecturer-defined priority is lexicographic: solve as many puzzles as
    # possible within the common time limit first.  Only then compare solution
    # quality, expanded nodes, and runtime.  The weighted performance score is
    # retained as a descriptive column, but it no longer controls the ranking.
    def final_order(item):
        gap = item["mean_solution_gap"]
        return (
            -item["success_rate"],
            gap if gap is not None else 999,
            item["mean_nodes_expanded"],
            item["median_runtime_seconds"],
        )

    for rank, row in enumerate(
        sorted(summary, key=final_order), start=1
    ):
        row["overall_rank"] = rank

    if generated:
        minimum_operators = min(max(1, row["operator_count"]) for row in generated)
        for row in generated:
            complexity_score = minimum_operators / max(1, row["operator_count"])
            row["generated_score"] = 0.90 * row["performance_score"] + 0.10 * complexity_score
        for rank, row in enumerate(
            sorted(
                generated,
                key=lambda item: final_order(item) + (item["operator_count"],),
            ),
            start=1,
        ):
            row["generated_rank"] = rank
    for row in summary:
        row.setdefault("generated_score", None)

    summary.sort(key=lambda row: row["overall_rank"])
    return summary


def save_benchmark_tables(rows, summary, output_directory, all_puzzles_summary=None):
    output_directory = Path(output_directory)
    _write_csv(output_directory / "heuristic_results_by_puzzle.csv", rows)
    _write_csv(output_directory / "heuristic_summary_and_ranking.csv", summary)
    if all_puzzles_summary is not None:
        _write_csv(
            output_directory / "heuristic_summary_all_40.csv",
            all_puzzles_summary,
        )


def save_experiment_summary(
    summary, evolved_records, output_directory, scope, seed_test_summary=None
):
    """Create a report-ready Markdown summary of the completed run."""
    output_directory = Path(output_directory)
    by_name = {row["heuristic"]: row for row in summary}
    lines = [
        "# GP/GEP Rush Hour Experiment Results",
        "",
        f"Final rankings below use **{scope}**.",
        "",
        "## Selected evolved heuristics",
        "",
        "| Method | Seeds | Infix expression | Operators | Validation fitness | Mean evolution time/seed | Test success | Mean gap | Mean nodes | Median runtime | Mean final behavioral diversity |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in evolved_records:
        result = by_name.get(f"{record['method']}_1", {})
        lines.append(
            "| {method} | {seeds} | `{expression}` | {operators} | {fitness:.4f} | "
            "{evolution:.2f}s | {success:.1%} | {gap:.4f} | {nodes:.1f} | "
            "{runtime:.4f}s | {diversity:.1%} |".format(
                method=record["method"],
                seeds=", ".join(map(str, record["seeds"])),
                expression=record["expression"].infix(),
                operators=record["expression"].operator_count(),
                fitness=record["validation_evaluation"].fitness,
                evolution=record["mean_evolution_seconds"],
                success=result.get("success_rate", 0.0),
                gap=result.get("mean_solution_gap") or 0.0,
                nodes=result.get("mean_nodes_expanded", 0.0),
                runtime=result.get("median_runtime_seconds", 0.0),
                diversity=record["mean_final_behavioral_diversity"],
            )
        )

    if seed_test_summary:
        lines.extend(
            [
                "",
                "## Multi-seed held-out stability",
                "",
                "Each row is the validation-best heuristic produced by one independent evolutionary run.",
                "",
                "| Method | Seed | Success | Mean gap | Mean nodes | Median runtime | Operators |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in sorted(seed_test_summary, key=lambda item: (item["method"], item["seed"])):
            gap = row["mean_solution_gap"]
            lines.append(
                f"| {row['method']} | {row['seed']} | {row['success_rate']:.1%} | "
                f"{(gap if gap is not None else 0.0):.4f} | "
                f"{row['mean_nodes_expanded']:.1f} | "
                f"{row['median_runtime_seconds']:.4f}s | "
                f"{row['operator_count']} |"
            )

    lines.extend(
        [
            "",
            "## Final ranking",
            "",
            "| Rank | Heuristic | Method | Solved | Success | Optimal among solved | Mean gap | Mean nodes | Median runtime | Operators | Quality rank | Node rank | Runtime rank |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary:
        operators = "-" if row["operator_count"] is None else row["operator_count"]
        gap = row["mean_solution_gap"] if row["mean_solution_gap"] is not None else 0.0
        lines.append(
            f"| {row['overall_rank']} | {row['heuristic']} | {row['method']} | "
            f"{row['solved']}/{row['total_puzzles']} | "
            f"{row['success_rate']:.1%} | "
            f"{(row['optimal_rate_among_solved'] or 0.0):.1%} | {gap:.4f} | "
            f"{row['mean_nodes_expanded']:.1f} | "
            f"{row['median_runtime_seconds']:.4f}s | {operators} | "
            f"{row['quality_rank']} | {row['node_efficiency_rank']} | "
            f"{row['runtime_rank']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Every heuristic receives the same wall-clock time limit on every final benchmark puzzle.",
            "- Overall rank is lexicographic: success rate first, then solution gap, expanded nodes, and runtime.",
            "- Expanded nodes are the primary stable measure of A* guidance; runtime is reported as the median of repeated runs.",
            "- Generated-heuristic complexity is the number of active expression operators. Inactive GEP tail symbols are not counted.",
            "- GP and GEP are evolved independently with multiple random seeds; seed-level outcomes are available in the seed-summary CSV files.",
            "- Structural and behavioral diversity histories, per-puzzle values, and all-40-puzzle summaries are available in the accompanying CSV files.",
            "",
        ]
    )
    path = output_directory / "EXPERIMENT_RESULTS.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError(
            "Plots require matplotlib. Install it with: pip install matplotlib"
        ) from error
    return plt


def plot_histories(gp_history, gep_history, output_directory):
    plt = _matplotlib()
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for label, history in (("GP", gp_history), ("GEP", gep_history)):
        by_generation = defaultdict(list)
        for row in history:
            by_generation[row["generation"]].append(row)
        generations = sorted(by_generation)
        axes[0].plot(
            generations,
            [mean(row["best_fitness"] for row in by_generation[g]) for g in generations],
            marker="o",
            markersize=3,
            label=f"{label} mean best",
        )
        axes[0].plot(
            generations,
            [mean(row["average_fitness"] for row in by_generation[g]) for g in generations],
            linestyle="--",
            label=f"{label} population mean",
        )
        axes[1].plot(
            generations,
            [mean(row["behavioral_diversity"] for row in by_generation[g]) for g in generations],
            marker="o",
            markersize=3,
            label=label,
        )

    axes[0].set_title("Fitness by generation")
    axes[0].set_xlabel("Generation")
    axes[0].set_ylabel("Fitness (higher is better)")
    axes[0].legend()
    axes[0].grid(alpha=0.25)
    axes[1].set_title("Behavioral diversity by generation")
    axes[1].set_xlabel("Generation")
    axes[1].set_ylabel("Unique behavior ratio")
    axes[1].set_ylim(0, 1.05)
    axes[1].legend()
    axes[1].grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "gp_vs_gep_evolution.png", dpi=180)
    plt.close(figure)


def plot_summary(summary, output_directory):
    plt = _matplotlib()
    output_directory = Path(output_directory)
    labels = [row["heuristic"] for row in summary]
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    metrics = (
        ("success_rate", "Success rate"),
        ("mean_nodes_expanded", "Mean expanded nodes"),
        ("median_runtime_seconds", "Median runtime (seconds)"),
        ("operator_count", "Active operator count"),
    )
    for axis, (key, title) in zip(axes.flat, metrics):
        values = [row[key] if row[key] is not None else 0 for row in summary]
        axis.bar(labels, values, color="#4472C4")
        axis.set_title(title)
        axis.tick_params(axis="x", rotation=25)
        axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "heuristic_comparison.png", dpi=180)
    plt.close(figure)
