# Rush Hour Heuristic Evolution with GP and GEP

This repository contains the implementation and experimental results for
**AI Lab Assignment 3 – Part B**. The project uses **Genetic Programming (GP)**
and **Gene Expression Programming (GEP)** to generate heuristic functions for
the Rush Hour puzzle.

Each evolved expression is converted into a normal `h(state)` function and
evaluated inside A*. The existing Rush Hour state representation, move
generator, goal test, and A* search are reused; the main contribution of this
part is the evolutionary heuristic-generation and evaluation layer.

## Experiment workflow

1. GP or GEP generates a candidate heuristic expression.
2. The expression is converted into `h(state)`.
3. A* uses the generated heuristic on several Rush Hour puzzles.
4. Search success, expanded nodes, runtime, and solution quality are measured.
5. The individual receives a fitness score with a complexity penalty.
6. Evolution applies selection and variation for 25 generations.
7. Candidates are selected on validation puzzles and evaluated once on the
   held-out test set.

## Heuristic representation

### Terminal set

The evolutionary algorithms construct expressions from numeric features of a
Rush Hour state:

| Terminal | Meaning |
|---|---|
| `D` | Distance of the target car `X` from the exit |
| `B` | Number of vehicles directly blocking `X` |
| `S` | Number of secondary vehicles blocking direct blockers |
| `K` | Direct blockers that cannot immediately clear the exit row |
| `M` | Available directions that immediately clear direct blockers |
| `C` | Minimum estimated blocker-clearance distance |
| `V` | Total number of vehicles |
| `L` | Number of legal successor moves |

### Function set

The shared function set is:

```text
+  -  *  protected_division  min  max  abs
```

Protected division prevents division-by-zero failures. Expression values are
bounded, negative heuristic values are converted to zero, and every evolved
heuristic returns zero at a goal state.

### GP

GP represents a heuristic directly as a variable-length expression tree. The
implementation uses:

- Ramped half-and-half initialization
- Tournament selection
- Subtree crossover
- Point and subtree mutation
- Elitism
- Maximum-depth control

### GEP

GEP represents a heuristic as a fixed-length chromosome. With a head length of
8 and maximum function arity of 2, the tail length is 9. The chromosome is
decoded into an active expression tree before evaluation.

The implementation uses:

- Mutation
- One-point and two-point crossover
- IS transposition
- RIS transposition
- Tournament selection and elitism

Only the active decoded expression is counted when measuring GEP complexity.

## Fitness and complexity bonus

Every individual is evaluated by running A* on the training puzzles. The loss
function is:

```text
loss = 20.0 * (1 - success_rate)
     + 0.50 * mean_node_ratio
     + 0.20 * mean_time_ratio
     + 0.20 * mean_solution_gap
     + 0.10 * complexity_ratio

fitness = 1 / (1 + loss)
```

The large failure penalty makes solving puzzles the first priority. Node and
time ratios compare a candidate with the Assignment 1 `h5` baseline. Solution
gap measures the difference from the reference solution length.

`complexity_ratio` is based on the number of active function/operator nodes.
Therefore, two similarly performing heuristics are distinguished in favor of
the simpler expression. This implements the assignment's required bonus for
heuristics with fewer calculations.

## Experimental configuration

The final experiment uses a fixed, balanced split of the 40 supplied puzzles:

| Setting | Value |
|---|---:|
| Training puzzles | 24 |
| Validation puzzles | 8 |
| Held-out test puzzles | 8 |
| Population size | 40 |
| Generations | 25 |
| Independent seeds | 42, 43, 44 |
| Fitness time limit | 2 seconds |
| Final A* time limit | 5 seconds per puzzle |
| Final node limit | Disabled |
| Runtime repetitions | 3 |
| Reported runtime | Median |

Each difficulty group of ten puzzles contributes six training, two validation,
and two test instances. The held-out test puzzles are:

```text
5, 10, 15, 20, 25, 30, 35, 40
```

The split and all parameters are stored in
`outputs_final/experiment_config.json`.

## Installation

The project was run with Python 3.13.

Create and activate an optional virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the plotting dependency:

```powershell
pip install -r requirements.txt
```

## Running the code

### Run the tests

```powershell
python -m unittest discover -s tests -v
```

### Run a short smoke experiment

This checks the complete workflow with a small population and only one
generation. It is not intended for report results.

```powershell
python run_part_b.py --quick --output outputs_smoke
```

### Run the complete experiment

```powershell
python run_part_b.py --output outputs_final
```

The complete experiment is computationally expensive because it evaluates GP
and GEP with three seeds and 24 training puzzles. The final completed outputs
are already included in `outputs_final`; rerunning is unnecessary unless a new
experiment is desired.

All available options can be viewed with:

```powershell
python run_part_b.py --help
```

## Final generated heuristics

The validation-selected expressions were:

| Method | Selected seed | Expression | Operators | Depth | Validation fitness |
|---|---:|---|---:|---:|---:|
| GP | 43 | `(((V * S) * B) * S)` | 3 | 4 | 0.6553 |
| GEP | 44 | `(((S * V) * (C * V)) * S)` | 4 | 4 | 0.6932 |

Equivalent simplified forms are:

```text
GP:  V * B * S^2
GEP: C * V^2 * S^2
```

The original trees, complete fitness components, selected seeds, and GEP
chromosome are stored in:

- `outputs_final/best_gp_heuristic.json`
- `outputs_final/best_gep_heuristic.json`

## Held-out test results

Every evaluated heuristic solved all eight held-out test puzzles within the
common five-second limit. The main differences were solution quality, expanded
nodes, runtime, and expression complexity.

| Heuristic | Role | Success | Mean solution gap | Mean expanded nodes | Median runtime | Operators |
|---|---|---:|---:|---:|---:|---:|
| `h4` | Original baseline | 100% | 0.0155 | 1810.4 | 0.1079 s | — |
| `h5` | Best Assignment 1 baseline | 100% | 0.0280 | 1821.8 | 0.0976 s | — |
| `GP_1` | Validation-selected GP | 100% | 0.0833 | 1943.4 | 0.0418 s | 3 |
| `GEP_1` | Validation-selected GEP | 100% | 0.0787 | 2570.5 | 0.0253 s | 4 |
| `GP_3` | Additional GP candidate | 100% | 0.0179 | **1769.1** | 0.0657 s | 7 |
| `GEP_3` | Additional GEP candidate | 100% | **0.0125** | 1835.9 | 0.0635 s | 3 |

Important observations:

- All original and evolved heuristics achieved a 100% success rate.
- `GP_3` achieved the lowest mean node count, expanding approximately 2.9%
  fewer nodes than `h5`.
- `GEP_3` achieved the best solution quality among evolved candidates, matching
  the reference length on seven of eight test puzzles.
- The validation-selected `GP_1` and `GEP_1` favored measured runtime over
  solution optimality and node efficiency.
- Results vary between puzzles, so no heuristic dominates every metric and
  every instance.

`GP_3` and `GEP_3` were members of the validation-selected candidate pool. They
are reported as additional candidates rather than replacements chosen after
examining the test set.

Runtime is an end-to-end measurement from the experiment machine and should be
interpreted together with the more stable expanded-node and solution-quality
metrics.

## GP versus GEP

| Measure | GP | GEP |
|---|---:|---:|
| Mean test success across seeds | 100% | 100% |
| Mean solution gap across seeds | 0.0600 | 0.0456 |
| Mean expanded nodes across seeds | 2009.5 | 2163.2 |
| Mean final behavioral diversity | 54.2% | 29.2% |
| Mean observed evolution time per seed | 2490.0 s | 736.8 s |
| Operator range | 3–7 | 3–5 |

GP maintained greater behavioral diversity and expanded fewer nodes on average.
GEP obtained a slightly lower average solution gap and required less observed
evolution time. The results demonstrate a trade-off: GP was stronger in
diversity and search guidance, while GEP provided compact expressions and
faster convergence.

## Output files

All report results are stored in `outputs_final`.

| File | Contents |
|---|---|
| `EXPERIMENT_RESULTS.md` | Report-ready overview of the completed run |
| `experiment_config.json` | Split, seeds, budgets, and evolutionary parameters |
| `best_gp_heuristic.json` | Selected GP expression, tree, fitness, and complexity |
| `best_gep_heuristic.json` | Selected GEP chromosome, expression, fitness, and complexity |
| `gp_history.csv` | GP fitness, complexity, diversity, and time by seed/generation |
| `gep_history.csv` | GEP fitness, complexity, diversity, and time by seed/generation |
| `gp_seed_summary.csv` | Validation result and diversity for every GP seed |
| `gep_seed_summary.csv` | Validation result and diversity for every GEP seed |
| `heuristic_results_by_puzzle.csv` | Detailed result for every puzzle and heuristic |
| `heuristic_summary_and_ranking.csv` | Primary held-out test summary and ranks |
| `heuristic_summary_all_40.csv` | Summary across all 40 puzzles |
| `multi_seed_test_results_by_puzzle.csv` | Per-puzzle test results for every seed |
| `multi_seed_test_summary.csv` | Held-out performance of each seed's best candidate |
| `optimal_lengths.json` | Reference solution lengths used for quality measurement |
| `gp_vs_gep_evolution.png` | Fitness convergence and behavioral diversity plot |
| `heuristic_comparison.png` | Success, nodes, runtime, and complexity comparison |

Use `outputs_final`, not smoke-test outputs, when preparing the report.

## Project structure

```text
LAB3_partB/
├── outputs_final/             # Completed final results
├── tests/
│   └── test_part_b.py
├── evolution_common.py        # Expressions, safe operations, h(state) wrapper
├── features.py                # Rush Hour terminal features
├── fitness.py                 # A*-based fitness and complexity bonus
├── generated_heuristics.py    # Loads saved expressions for reuse
├── gp_engine.py               # Genetic Programming implementation
├── gep_engine.py              # Gene Expression Programming implementation
├── heuristics.py              # Original Rush Hour heuristics
├── search.py                  # BFS and A* search
├── state.py                   # Rush Hour state representation
├── moves.py                   # Legal successor generation
├── parser.py                  # Puzzle loader
├── reporting.py               # CSV, JSON, Markdown, and plot generation
├── run_part_b.py              # Complete Part B experiment
├── rh.txt                     # 40 Rush Hour puzzles
├── requirements.txt
└── README.md
```

## Reproducibility

- The train/validation/test split is fixed and stored in the configuration.
- GP and GEP use the same population size, generations, feature/function sets,
  puzzles, budgets, and seeds.
- Three independent seeds are reported instead of relying on one evolutionary
  run.
- Final runtimes are medians of three repetitions.
- Detailed per-puzzle data are included so summary values can be verified.
