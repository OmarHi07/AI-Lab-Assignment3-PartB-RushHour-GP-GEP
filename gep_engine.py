"""Fixed-length Gene Expression Programming implementation."""

import random
import time
from collections import deque
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


TERMINAL_SYMBOLS = tuple(TERMINAL_NAMES) + tuple(
    constant_symbol(value) for value in CONSTANTS
)


@dataclass
class GEPEvolutionResult:
    best_chromosome: list
    best_expression: ExpressionNode
    best_evaluation: object
    history: list
    top_individuals: list
    generation_time_seconds: float
    head_length: int
    tail_length: int


def tail_length(head_length):
    maximum_arity = max(FUNCTION_ARITY.values())
    return head_length * (maximum_arity - 1) + 1


def random_chromosome(rng, head_length):
    tail = tail_length(head_length)
    head_alphabet = FUNCTION_NAMES + TERMINAL_SYMBOLS
    return [rng.choice(head_alphabet) for _ in range(head_length)] + [
        rng.choice(TERMINAL_SYMBOLS) for _ in range(tail)
    ]


def decode_chromosome(chromosome):
    """Decode the active K-expression into its expression tree phenotype."""
    root = ExpressionNode(chromosome[0])
    pending = deque([root] if root.symbol in FUNCTION_ARITY else [])
    cursor = 1

    while pending:
        parent = pending.popleft()
        for _ in range(FUNCTION_ARITY[parent.symbol]):
            child = ExpressionNode(chromosome[cursor])
            cursor += 1
            parent.children.append(child)
            if child.symbol in FUNCTION_ARITY:
                pending.append(child)
    return root


def mutate(chromosome, rng, head_length):
    child = chromosome[:]
    index = rng.randrange(len(child))
    alphabet = (
        FUNCTION_NAMES + TERMINAL_SYMBOLS
        if index < head_length
        else TERMINAL_SYMBOLS
    )
    alternatives = [symbol for symbol in alphabet if symbol != child[index]]
    child[index] = rng.choice(alternatives)
    return child


def one_point_crossover(parent_a, parent_b, rng):
    point = rng.randrange(1, len(parent_a))
    return parent_a[:point] + parent_b[point:]


def two_point_crossover(parent_a, parent_b, rng):
    left, right = sorted(rng.sample(range(1, len(parent_a)), 2))
    return parent_a[:left] + parent_b[left:right] + parent_a[right:]


def is_transposition(chromosome, rng, head_length):
    """Insert a copied sequence inside the head while keeping the root fixed."""
    child = chromosome[:]
    segment_length = rng.randint(1, min(3, head_length - 1))
    start = rng.randrange(0, len(child) - segment_length + 1)
    segment = child[start : start + segment_length]
    insertion = rng.randrange(1, head_length)
    head = child[:head_length]
    head[insertion:insertion] = segment
    return head[:head_length] + child[head_length:]


def ris_transposition(chromosome, rng, head_length):
    """Move a head segment beginning with a function to the root."""
    function_positions = [
        index
        for index, symbol in enumerate(chromosome[:head_length])
        if symbol in FUNCTION_ARITY
    ]
    if not function_positions:
        return chromosome[:]
    start = rng.choice(function_positions)
    segment_length = rng.randint(1, min(3, head_length - start))
    segment = chromosome[start : start + segment_length]
    head = segment + chromosome[:head_length]
    return head[:head_length] + chromosome[head_length:]


def _tournament(population, evaluations, rng, tournament_size):
    choices = rng.sample(range(len(population)), min(tournament_size, len(population)))
    winner = max(choices, key=lambda index: evaluations[index].fitness)
    return population[winner]


def _diversity(population, expressions, probe_states):
    genotypic = len({tuple(chromosome) for chromosome in population}) / len(population)
    structural = len({expression.prefix() for expression in expressions}) / len(population)
    signatures = set()
    for expression in expressions:
        heuristic = make_heuristic(expression)
        signatures.add(tuple(round(heuristic(state), 6) for state in probe_states))
    return genotypic, structural, len(signatures) / len(population)


def evolve_gep(
    evaluator,
    population_size=40,
    generations=25,
    head_length_value=8,
    crossover_rate=0.65,
    mutation_rate=0.20,
    transposition_rate=0.10,
    elite_size=2,
    tournament_size=3,
    seed=42,
):
    rng = random.Random(seed)
    population = [
        random_chromosome(rng, head_length_value) for _ in range(population_size)
    ]
    history = []
    total_start = time.perf_counter()
    probe_states = [benchmark.state for benchmark in evaluator.benchmarks]

    for generation in range(generations + 1):
        generation_start = time.perf_counter()
        expressions = [decode_chromosome(chromosome) for chromosome in population]
        evaluations = [evaluator(expression) for expression in expressions]
        ranking = sorted(
            range(len(population)),
            key=lambda index: evaluations[index].fitness,
            reverse=True,
        )
        best_index = ranking[0]
        genotypic, structural, behavioral = _diversity(
            population, expressions, probe_states
        )
        history.append(
            {
                "generation": generation,
                "best_fitness": evaluations[best_index].fitness,
                "average_fitness": sum(item.fitness for item in evaluations)
                / len(evaluations),
                "best_prefix": expressions[best_index].prefix(),
                "best_operator_count": expressions[best_index].operator_count(),
                "average_operator_count": sum(
                    expression.operator_count() for expression in expressions
                )
                / len(expressions),
                "genotypic_diversity": genotypic,
                "structural_diversity": structural,
                "behavioral_diversity": behavioral,
                "generation_time_seconds": time.perf_counter() - generation_start,
                "actual_fitness_evaluations": evaluator.actual_evaluations,
            }
        )

        if generation == generations:
            break

        next_population = [population[index][:] for index in ranking[:elite_size]]
        while len(next_population) < population_size:
            roll = rng.random()
            parent = _tournament(
                population, evaluations, rng, tournament_size
            )
            if roll < crossover_rate:
                other = _tournament(
                    population, evaluations, rng, tournament_size
                )
                if rng.random() < 0.5:
                    child = one_point_crossover(parent, other, rng)
                else:
                    child = two_point_crossover(parent, other, rng)
            elif roll < crossover_rate + mutation_rate:
                child = mutate(parent, rng, head_length_value)
            elif roll < crossover_rate + mutation_rate + transposition_rate:
                if rng.random() < 0.5:
                    child = is_transposition(parent, rng, head_length_value)
                else:
                    child = ris_transposition(parent, rng, head_length_value)
            else:
                child = parent[:]
            next_population.append(child)
        population = next_population

    final_expressions = [decode_chromosome(chromosome) for chromosome in population]
    final_evaluations = [evaluator(expression) for expression in final_expressions]
    final_ranking = sorted(
        range(len(population)),
        key=lambda index: final_evaluations[index].fitness,
        reverse=True,
    )
    top = [
        (
            population[index][:],
            final_expressions[index].clone(),
            final_evaluations[index],
        )
        for index in final_ranking[: min(10, len(population))]
    ]
    return GEPEvolutionResult(
        best_chromosome=top[0][0],
        best_expression=top[0][1],
        best_evaluation=top[0][2],
        history=history,
        top_individuals=top,
        generation_time_seconds=time.perf_counter() - total_start,
        head_length=head_length_value,
        tail_length=tail_length(head_length_value),
    )
