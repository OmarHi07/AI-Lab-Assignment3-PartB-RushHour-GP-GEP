"""Run the complete Assignment 3 Part B GP/GEP experiment."""

import argparse
import json
from pathlib import Path
from statistics import mean

from evolution_common import make_heuristic
from fitness import DEFAULT_TRAIN_IDS, DEFAULT_VALIDATION_IDS, FitnessEvaluator, build_benchmarks
from gep_engine import evolve_gep
from gp_engine import evolve_gp
from heuristics import h1, h2, h4, h5, h_admissible
from parser import load_puzzles
from reporting import (
    benchmark_heuristics,
    combine_seed_histories,
    plot_histories,
    plot_summary,
    save_benchmark_tables,
    save_evolved_model,
    save_experiment_summary,
    save_history,
    save_multi_seed_test_tables,
    save_seed_summary,
    summarize_benchmarks,
)
from search import astar, bfs


def parse_ids(text):
    return tuple(int(value.strip()) for value in text.split(",") if value.strip())


def validate_problem_split(train_ids, validation_ids, puzzle_count):
    all_selected = train_ids + validation_ids
    if len(set(train_ids)) != len(train_ids):
        raise ValueError("Training problem IDs contain duplicates")
    if len(set(validation_ids)) != len(validation_ids):
        raise ValueError("Validation problem IDs contain duplicates")
    overlap = set(train_ids) & set(validation_ids)
    if overlap:
        raise ValueError(f"Train/validation overlap: {sorted(overlap)}")
    invalid = [problem for problem in all_selected if not 1 <= problem <= puzzle_count]
    if invalid:
        raise ValueError(f"Problem IDs outside 1..{puzzle_count}: {invalid}")


def unique_gp_candidates(seed_results):
    chosen = []
    seen = set()
    for seed, result in seed_results:
        for expression, evaluation in result.top_individuals:
            if expression.prefix() not in seen:
                chosen.append((expression, evaluation, seed))
                seen.add(expression.prefix())
    return chosen


def unique_gep_candidates(seed_results):
    chosen = []
    seen = set()
    for seed, result in seed_results:
        for chromosome, expression, evaluation in result.top_individuals:
            if expression.prefix() not in seen:
                chosen.append((chromosome, expression, evaluation, seed))
                seen.add(expression.prefix())
    return chosen


def select_gp_on_validation(seed_results, evaluator, count):
    candidates = unique_gp_candidates(seed_results)
    ranked = sorted(
        (
            (expression, evaluator(expression), seed)
            for expression, _, seed in candidates
        ),
        key=lambda item: item[1].fitness,
        reverse=True,
    )
    return ranked[:count]


def select_gep_on_validation(seed_results, evaluator, count):
    candidates = unique_gep_candidates(seed_results)
    ranked = sorted(
        (
            (chromosome, expression, evaluator(expression), seed)
            for chromosome, expression, _, seed in candidates
        ),
        key=lambda item: item[2].fitness,
        reverse=True,
    )
    return ranked[:count]


def compute_optimal_lengths(puzzles, problem_ids, time_limit_seconds):
    depths = {}
    for problem in problem_ids:
        result = bfs(
            puzzles[problem - 1], time_limit_seconds=time_limit_seconds
        )
        depths[problem] = result["solution_length"] if result["success"] else None
    return depths


def fill_missing_optimal_lengths(rows, optimal_lengths):
    """Use the best found length only when BFS exceeded its safety timeout."""
    for problem, optimal in list(optimal_lengths.items()):
        if optimal is not None:
            continue
        lengths = [
            row["solution_length"]
            for row in rows
            if row["problem"] == problem and row["success"]
        ]
        if lengths:
            optimal_lengths[problem] = min(lengths)

    for row in rows:
        optimal = optimal_lengths.get(row["problem"])
        row["optimal_length"] = optimal
        if row["success"] and optimal is not None:
            row["solution_gap"] = max(
                0.0, (row["solution_length"] - optimal) / max(1, optimal)
            )


def expression_spec(method, rank, expression):
    return {
        "function": make_heuristic(expression),
        "method": method,
        "operator_count": expression.operator_count(),
        "tree_depth": expression.depth(),
        "prefix": expression.prefix(),
        "infix": expression.infix(),
        "rank": rank,
    }


def selected_run(seed_results, selected_seed):
    return next(result for seed, result in seed_results if seed == selected_seed)


def seed_summary_rows(method, seed_results, validation_evaluator, selected_prefix):
    rows = []
    for seed, result in seed_results:
        if method == "GP":
            expression, evaluation, _ = select_gp_on_validation(
                [(seed, result)], validation_evaluator, 1
            )[0]
        else:
            _, expression, evaluation, _ = select_gep_on_validation(
                [(seed, result)], validation_evaluator, 1
            )[0]
        rows.append(
            {
                "seed": seed,
                "best_validation_expression": expression.infix(),
                "best_validation_fitness": evaluation.fitness,
                "best_validation_success_rate": evaluation.success_rate,
                "best_validation_mean_node_ratio": evaluation.mean_node_ratio,
                "best_validation_mean_time_ratio": evaluation.mean_time_ratio,
                "operator_count": expression.operator_count(),
                "evolution_time_seconds": result.generation_time_seconds,
                "final_structural_diversity": result.history[-1][
                    "structural_diversity"
                ],
                "final_behavioral_diversity": result.history[-1][
                    "behavioral_diversity"
                ],
                "globally_selected": int(expression.prefix() == selected_prefix),
            }
        )
    return rows


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Evolve and compare GP/GEP Rush Hour heuristics"
    )
    parser.add_argument("--mode", choices=("gp", "gep", "both"), default="both")
    parser.add_argument("--population", type=int, default=40)
    parser.add_argument("--generations", type=int, default=25)
    parser.add_argument(
        "--seeds",
        default="42,43,44",
        help="Comma-separated independent GP/GEP seeds (default: 42,43,44)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Backward-compatible single-seed override",
    )
    parser.add_argument("--train-ids", default=",".join(map(str, DEFAULT_TRAIN_IDS)))
    parser.add_argument(
        "--validation-ids", default=",".join(map(str, DEFAULT_VALIDATION_IDS))
    )
    parser.add_argument(
        "--fitness-node-limit",
        type=int,
        default=0,
        help="Optional safety node limit; 0 disables it (time limit remains active)",
    )
    parser.add_argument("--fitness-time-limit", type=float, default=2.0)
    parser.add_argument(
        "--final-node-limit",
        type=int,
        default=0,
        help="Optional final safety node limit; 0 disables it",
    )
    parser.add_argument("--final-time-limit", type=float, default=5.0)
    parser.add_argument("--optimal-time-limit", type=float, default=5.0)
    parser.add_argument("--timing-repetitions", type=int, default=3)
    parser.add_argument("--top-candidates", type=int, default=3)
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--skip-plots", action="store_true")
    return parser


def main():
    args = build_argument_parser().parse_args()
    project_directory = Path(__file__).resolve().parent
    output_directory = project_directory / args.output
    output_directory.mkdir(parents=True, exist_ok=True)
    puzzles = load_puzzles(project_directory / "rh.txt")

    train_ids = parse_ids(args.train_ids)
    validation_ids = parse_ids(args.validation_ids)
    validate_problem_split(train_ids, validation_ids, len(puzzles))
    seeds = (args.seed,) if args.seed is not None else parse_ids(args.seeds)
    if not seeds:
        raise ValueError("At least one random seed is required")
    fitness_node_limit = args.fitness_node_limit or None
    final_node_limit = args.final_node_limit or None
    final_ids = tuple(range(1, len(puzzles) + 1))
    if args.quick:
        args.population = min(args.population, 6)
        args.generations = min(args.generations, 1)
        fitness_node_limit = min(fitness_node_limit or 1_000, 1_000)
        final_node_limit = min(final_node_limit or 2_000, 2_000)
        args.timing_repetitions = 1
        seeds = seeds[:1]
        train_ids = train_ids[:2]
        validation_ids = validation_ids[:2]
        final_ids = tuple(sorted(set(train_ids + validation_ids)))

    test_ids = tuple(
        problem
        for problem in final_ids
        if problem not in set(train_ids) | set(validation_ids)
    )

    config = {
        "mode": args.mode,
        "population": args.population,
        "generations": args.generations,
        "seeds": seeds,
        "training_problems": train_ids,
        "validation_problems": validation_ids,
        "held_out_test_problems": test_ids,
        "split_counts": {
            "train": len(train_ids),
            "validation": len(validation_ids),
            "test": len(test_ids),
        },
        "final_problems": final_ids,
        "fitness_node_limit": fitness_node_limit,
        "fitness_time_limit": args.fitness_time_limit,
        "final_node_limit": final_node_limit,
        "final_time_limit": args.final_time_limit,
        "timing_repetitions": args.timing_repetitions,
        "ranking_priority": [
            "success_rate",
            "solution_quality",
            "nodes_expanded",
            "runtime",
        ],
        "primary_assignment_1_baseline": "h5",
        "secondary_assignment_1_baseline": "h4",
    }
    (output_directory / "experiment_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    print("Preparing fixed h5/h4 and BFS training references...")
    benchmarks = build_benchmarks(
        puzzles,
        train_ids,
        time_limit_seconds=args.final_time_limit,
        node_limit=final_node_limit,
        optimal_time_limit_seconds=args.optimal_time_limit,
    )
    print("Preparing held-out validation references...")
    validation_benchmarks = build_benchmarks(
        puzzles,
        validation_ids,
        time_limit_seconds=args.final_time_limit,
        node_limit=final_node_limit,
        optimal_time_limit_seconds=args.optimal_time_limit,
    )

    gp_results = []
    gep_results = []
    selected_gp = []
    selected_gep = []
    if args.mode in ("gp", "both"):
        for seed in seeds:
            print(f"Evolving GP heuristics (seed {seed})...")
            gp_evaluator = FitnessEvaluator(
                benchmarks,
                time_limit_seconds=args.fitness_time_limit,
                node_limit=fitness_node_limit,
            )
            gp_results.append(
                (
                    seed,
                    evolve_gp(
                        gp_evaluator,
                        population_size=args.population,
                        generations=args.generations,
                        seed=seed,
                    ),
                )
            )
        gp_validation_evaluator = FitnessEvaluator(
            validation_benchmarks,
            time_limit_seconds=args.fitness_time_limit,
            node_limit=fitness_node_limit,
        )
        selected_gp = select_gp_on_validation(
            gp_results, gp_validation_evaluator, args.top_candidates
        )
        gp_history = combine_seed_histories(gp_results)
        save_history("GP", gp_history, output_directory)
        gp_seed_rows = seed_summary_rows(
            "GP",
            gp_results,
            gp_validation_evaluator,
            selected_gp[0][0].prefix(),
        )
        save_seed_summary("GP", gp_seed_rows, output_directory)
        gp_selected_result = selected_run(gp_results, selected_gp[0][2])
        save_evolved_model(
            "GP",
            selected_gp[0][0],
            selected_gp[0][1],
            output_directory,
            gp_selected_result.generation_time_seconds,
            extra={
                "selection_set": "validation",
                "selected_seed": selected_gp[0][2],
                "seeds": seeds,
                "mean_evolution_time_seconds": mean(
                    result.generation_time_seconds for _, result in gp_results
                ),
                "total_evolution_time_seconds": sum(
                    result.generation_time_seconds for _, result in gp_results
                ),
                "best_training_fitness": gp_selected_result.best_evaluation.fitness,
            },
        )
        print(
            f"Validation-selected GP (seed {selected_gp[0][2]}):",
            selected_gp[0][0].infix(),
        )

    if args.mode in ("gep", "both"):
        for seed in seeds:
            print(f"Evolving GEP heuristics (seed {seed})...")
            gep_evaluator = FitnessEvaluator(
                benchmarks,
                time_limit_seconds=args.fitness_time_limit,
                node_limit=fitness_node_limit,
            )
            gep_results.append(
                (
                    seed,
                    evolve_gep(
                        gep_evaluator,
                        population_size=args.population,
                        generations=args.generations,
                        seed=seed,
                    ),
                )
            )
        gep_validation_evaluator = FitnessEvaluator(
            validation_benchmarks,
            time_limit_seconds=args.fitness_time_limit,
            node_limit=fitness_node_limit,
        )
        selected_gep = select_gep_on_validation(
            gep_results, gep_validation_evaluator, args.top_candidates
        )
        gep_history = combine_seed_histories(gep_results)
        save_history("GEP", gep_history, output_directory)
        gep_seed_rows = seed_summary_rows(
            "GEP",
            gep_results,
            gep_validation_evaluator,
            selected_gep[0][1].prefix(),
        )
        save_seed_summary("GEP", gep_seed_rows, output_directory)
        gep_selected_result = selected_run(gep_results, selected_gep[0][3])
        save_evolved_model(
            "GEP",
            selected_gep[0][1],
            selected_gep[0][2],
            output_directory,
            gep_selected_result.generation_time_seconds,
            chromosome=selected_gep[0][0],
            extra={
                "head_length": gep_selected_result.head_length,
                "tail_length": gep_selected_result.tail_length,
                "selection_set": "validation",
                "selected_seed": selected_gep[0][3],
                "seeds": seeds,
                "mean_evolution_time_seconds": mean(
                    result.generation_time_seconds for _, result in gep_results
                ),
                "total_evolution_time_seconds": sum(
                    result.generation_time_seconds for _, result in gep_results
                ),
                "best_training_fitness": gep_selected_result.best_evaluation.fitness,
            },
        )
        print(
            f"Validation-selected GEP (seed {selected_gep[0][3]}):",
            selected_gep[0][1].infix(),
        )

    heuristic_specs = {
        "h1": {"function": h1, "method": "Original"},
        "h2": {"function": h2, "method": "Original"},
        "h4": {"function": h4, "method": "Original"},
        "h_admissible": {"function": h_admissible, "method": "Original"},
        "h5": {"function": h5, "method": "Original"},
    }
    if selected_gp:
        for rank, (expression, _, _) in enumerate(selected_gp, start=1):
            heuristic_specs[f"GP_{rank}"] = expression_spec("GP", rank, expression)
    if selected_gep:
        for rank, (_, expression, _, _) in enumerate(selected_gep, start=1):
            heuristic_specs[f"GEP_{rank}"] = expression_spec("GEP", rank, expression)

    print("Computing final solution-quality references...")
    optimal_lengths = compute_optimal_lengths(
        puzzles, final_ids, args.optimal_time_limit
    )
    print("Benchmarking original and generated heuristics...")
    rows = benchmark_heuristics(
        puzzles,
        heuristic_specs,
        astar,
        final_ids,
        optimal_lengths,
        time_limit_seconds=args.final_time_limit,
        node_limit=final_node_limit,
        timing_repetitions=args.timing_repetitions,
        problem_splits={
            **{problem: "train" for problem in train_ids},
            **{problem: "validation" for problem in validation_ids},
            **{problem: "test" for problem in test_ids},
        },
    )
    fill_missing_optimal_lengths(rows, optimal_lengths)
    all_summary = summarize_benchmarks(rows)
    test_rows = [row for row in rows if row["split"] == "test"]
    summary = summarize_benchmarks(test_rows or rows)
    save_benchmark_tables(
        rows, summary, output_directory, all_puzzles_summary=all_summary
    )
    (output_directory / "optimal_lengths.json").write_text(
        json.dumps(optimal_lengths, indent=2), encoding="utf-8"
    )

    # Evaluate the validation-best heuristic from every seed on the held-out
    # test set.  This is kept separate from the primary ranking so stability
    # evidence does not clutter the baseline-versus-selected comparison.
    seed_specs = {}
    if gp_results:
        for seed, result in gp_results:
            expression, _, _ = select_gp_on_validation(
                [(seed, result)], gp_validation_evaluator, 1
            )[0]
            seed_specs[f"GP_seed_{seed}"] = {
                **expression_spec("GP", 1, expression),
                "seed": seed,
            }
    if gep_results:
        for seed, result in gep_results:
            _, expression, _, _ = select_gep_on_validation(
                [(seed, result)], gep_validation_evaluator, 1
            )[0]
            seed_specs[f"GEP_seed_{seed}"] = {
                **expression_spec("GEP", 1, expression),
                "seed": seed,
            }

    seed_test_summary = []
    if seed_specs:
        seed_scope_ids = test_ids or final_ids
        seed_test_rows = benchmark_heuristics(
            puzzles,
            seed_specs,
            astar,
            seed_scope_ids,
            optimal_lengths,
            time_limit_seconds=args.final_time_limit,
            node_limit=final_node_limit,
            timing_repetitions=args.timing_repetitions,
            problem_splits={problem: "test" for problem in seed_scope_ids},
        )
        seed_test_summary = summarize_benchmarks(seed_test_rows)
        save_multi_seed_test_tables(
            seed_test_rows, seed_test_summary, output_directory
        )

    if not args.skip_plots:
        if gp_results and gep_results:
            plot_histories(gp_history, gep_history, output_directory)
        plot_summary(summary, output_directory)

    ranking_scope = "held-out test puzzles" if test_rows else "quick-run puzzles"
    evolved_records = []
    if gp_results and selected_gp:
        evolved_records.append(
            {
                "method": "GP",
                "expression": selected_gp[0][0],
                "validation_evaluation": selected_gp[0][1],
                "seeds": seeds,
                "mean_evolution_seconds": mean(
                    result.generation_time_seconds for _, result in gp_results
                ),
                "mean_final_behavioral_diversity": mean(
                    result.history[-1]["behavioral_diversity"]
                    for _, result in gp_results
                ),
            }
        )
    if gep_results and selected_gep:
        evolved_records.append(
            {
                "method": "GEP",
                "expression": selected_gep[0][1],
                "validation_evaluation": selected_gep[0][2],
                "seeds": seeds,
                "mean_evolution_seconds": mean(
                    result.generation_time_seconds for _, result in gep_results
                ),
                "mean_final_behavioral_diversity": mean(
                    result.history[-1]["behavioral_diversity"]
                    for _, result in gep_results
                ),
            }
        )
    save_experiment_summary(
        summary,
        evolved_records,
        output_directory,
        ranking_scope,
        seed_test_summary=seed_test_summary,
    )

    print(f"\nFinal ranking ({ranking_scope})")
    for row in summary:
        print(
            f"{row['overall_rank']:>2}. {row['heuristic']:<14} "
            f"solved={row['solved']}/{row['total_puzzles']} "
            f"success={row['success_rate']:.1%} "
            f"nodes={row['mean_nodes_expanded']:.1f} "
            f"runtime={row['median_runtime_seconds']:.4f}s"
        )
    print("\nResults saved in:", output_directory)


if __name__ == "__main__":
    main()
