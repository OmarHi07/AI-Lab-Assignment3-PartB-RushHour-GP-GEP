"""Small, course-aligned tree Genetic Programming implementation."""

import random
import time
from dataclasses import dataclass

from evolution_common import (
    CONSTANTS,
    FUNCTION_ARITY,
    FUNCTION_NAMES,
    ExpressionNode,
    constant_symbol,
    make_heuristic,
)
from features import TERMINAL_NAMES


@dataclass
class GPEvolutionResult:
    best_expression: ExpressionNode
    best_evaluation: object
    history: list
    top_individuals: list
    generation_time_seconds: float


def _random_terminal(rng):
    if rng.random() < 0.75:
        return ExpressionNode(rng.choice(TERMINAL_NAMES))
    return ExpressionNode(constant_symbol(rng.choice(CONSTANTS)))


def random_tree(rng, maximum_depth, method="grow", current_depth=1):
    must_stop = current_depth >= maximum_depth
    grow_stop = method == "grow" and current_depth > 1 and rng.random() < 0.35
    if must_stop or grow_stop:
        return _random_terminal(rng)

    function = rng.choice(FUNCTION_NAMES)
    return ExpressionNode(
        function,
        [
            random_tree(rng, maximum_depth, method, current_depth + 1)
            for _ in range(FUNCTION_ARITY[function])
        ],
    )


def ramped_half_and_half(rng, population_size, maximum_initial_depth):
    population = []
    depths = list(range(2, maximum_initial_depth + 1))
    for index in range(population_size):
        method = "full" if index % 2 == 0 else "grow"
        population.append(random_tree(rng, depths[index % len(depths)], method))
    rng.shuffle(population)
    return population


def _paths(root, want_functions=None):
    found = []

    def visit(node, path):
        is_function = node.symbol in FUNCTION_ARITY
        if want_functions is None or want_functions == is_function:
            found.append(path)
        for child_index, child in enumerate(node.children):
            visit(child, path + (child_index,))

    visit(root, ())
    return found


def _node_at(root, path):
    node = root
    for child_index in path:
        node = node.children[child_index]
    return node


def _replace(root, path, replacement):
    if not path:
        return replacement.clone()
    parent = _node_at(root, path[:-1])
    parent.children[path[-1]] = replacement.clone()
    return root


def _variation_path(root, rng):
    # Lecture 8 recommends favoring internal crossover points to avoid swaps
    # that merely exchange leaves.
    internal = _paths(root, want_functions=True)
    terminals = _paths(root, want_functions=False)
    if internal and rng.random() < 0.90:
        return rng.choice(internal)
    return rng.choice(terminals or internal)


def subtree_crossover(parent_a, parent_b, rng, maximum_depth):
    child = parent_a.clone()
    path_a = _variation_path(child, rng)
    path_b = _variation_path(parent_b, rng)
    child = _replace(child, path_a, _node_at(parent_b, path_b))
    return child if child.depth() <= maximum_depth else parent_a.clone()


def point_mutation(parent, rng):
    child = parent.clone()
    path = rng.choice(_paths(child))
    node = _node_at(child, path)

    if node.symbol in FUNCTION_ARITY:
        same_arity = [
            name
            for name, arity in FUNCTION_ARITY.items()
            if arity == FUNCTION_ARITY[node.symbol] and name != node.symbol
        ]
        if same_arity:
            node.symbol = rng.choice(same_arity)
    else:
        replacement = _random_terminal(rng)
        node.symbol = replacement.symbol
    return child


def subtree_mutation(parent, rng, maximum_depth):
    child = parent.clone()
    path = _variation_path(child, rng)
    allowed_subtree_depth = max(1, maximum_depth - len(path))
    replacement = random_tree(rng, min(3, allowed_subtree_depth), "grow")
    child = _replace(child, path, replacement)
    return child if child.depth() <= maximum_depth else parent.clone()


def _tournament(population, evaluations, rng, tournament_size):
    choices = rng.sample(range(len(population)), min(tournament_size, len(population)))
    winner = max(choices, key=lambda index: evaluations[index].fitness)
    return population[winner]


def _diversity(population, probe_states):
    structural = len({individual.prefix() for individual in population}) / len(population)
    signatures = set()
    for individual in population:
        heuristic = make_heuristic(individual)
        signatures.add(tuple(round(heuristic(state), 6) for state in probe_states))
    return structural, len(signatures) / len(population)


def evolve_gp(
    evaluator,
    population_size=40,
    generations=25,
    maximum_initial_depth=4,
    maximum_depth=6,
    crossover_rate=0.70,
    mutation_rate=0.25,
    elite_size=2,
    tournament_size=3,
    seed=42,
):
    rng = random.Random(seed)
    population = ramped_half_and_half(
        rng, population_size, maximum_initial_depth
    )
    history = []
    total_start = time.perf_counter()
    probe_states = [benchmark.state for benchmark in evaluator.benchmarks]

    for generation in range(generations + 1):
        generation_start = time.perf_counter()
        evaluations = [evaluator(individual) for individual in population]
        ranking = sorted(
            range(len(population)),
            key=lambda index: evaluations[index].fitness,
            reverse=True,
        )
        best_index = ranking[0]
        structural, behavioral = _diversity(population, probe_states)
        history.append(
            {
                "generation": generation,
                "best_fitness": evaluations[best_index].fitness,
                "average_fitness": sum(item.fitness for item in evaluations)
                / len(evaluations),
                "best_prefix": population[best_index].prefix(),
                "best_operator_count": population[best_index].operator_count(),
                "average_operator_count": sum(
                    individual.operator_count() for individual in population
                )
                / len(population),
                "structural_diversity": structural,
                "behavioral_diversity": behavioral,
                "generation_time_seconds": time.perf_counter() - generation_start,
                "actual_fitness_evaluations": evaluator.actual_evaluations,
            }
        )

        if generation == generations:
            break

        next_population = [population[index].clone() for index in ranking[:elite_size]]
        while len(next_population) < population_size:
            roll = rng.random()
            parent = _tournament(
                population, evaluations, rng, tournament_size
            )
            if roll < crossover_rate:
                other = _tournament(
                    population, evaluations, rng, tournament_size
                )
                child = subtree_crossover(parent, other, rng, maximum_depth)
            elif roll < crossover_rate + mutation_rate:
                if rng.random() < 0.5:
                    child = point_mutation(parent, rng)
                else:
                    child = subtree_mutation(parent, rng, maximum_depth)
            else:
                child = parent.clone()
            next_population.append(child)
        population = next_population

    final_evaluations = [evaluator(individual) for individual in population]
    final_ranking = sorted(
        range(len(population)),
        key=lambda index: final_evaluations[index].fitness,
        reverse=True,
    )
    top = [
        (population[index].clone(), final_evaluations[index])
        for index in final_ranking[: min(10, len(population))]
    ]
    return GPEvolutionResult(
        best_expression=top[0][0],
        best_evaluation=top[0][1],
        history=history,
        top_individuals=top,
        generation_time_seconds=time.perf_counter() - total_start,
    )
