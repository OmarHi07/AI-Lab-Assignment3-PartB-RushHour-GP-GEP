# GP/GEP Rush Hour Experiment Results

Final rankings below use **held-out test puzzles**.

## Selected evolved heuristics

| Method | Seeds | Infix expression | Operators | Validation fitness | Mean evolution time/seed | Test success | Mean gap | Mean nodes | Median runtime | Mean final behavioral diversity |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GP | 42, 43, 44 | `(((V * S) * B) * S)` | 3 | 0.6553 | 2490.00s | 100.0% | 0.0833 | 1943.4 | 0.0418s | 54.2% |
| GEP | 42, 43, 44 | `(((S * V) * (C * V)) * S)` | 4 | 0.6932 | 736.81s | 100.0% | 0.0787 | 2570.5 | 0.0253s | 29.2% |

## Multi-seed held-out stability

Each row is the validation-best heuristic produced by one independent evolutionary run.

| Method | Seed | Success | Mean gap | Mean nodes | Median runtime | Operators |
|---|---:|---:|---:|---:|---:|---:|
| GEP | 42 | 100.0% | 0.0458 | 2083.1 | 0.0786s | 5 |
| GEP | 43 | 100.0% | 0.0125 | 1835.9 | 0.0602s | 3 |
| GEP | 44 | 100.0% | 0.0787 | 2570.5 | 0.0289s | 4 |
| GP | 42 | 100.0% | 0.0787 | 2316.0 | 0.0294s | 5 |
| GP | 43 | 100.0% | 0.0833 | 1943.4 | 0.0398s | 3 |
| GP | 44 | 100.0% | 0.0179 | 1769.1 | 0.0673s | 7 |

## Final ranking

| Rank | Heuristic | Method | Solved | Success | Optimal among solved | Mean gap | Mean nodes | Median runtime | Operators | Quality rank | Node rank | Runtime rank |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | h_admissible | Original | 8/8 | 100.0% | 100.0% | 0.0000 | 2251.1 | 0.1262s | - | 1 | 8 | 11 |
| 2 | h1 | Original | 8/8 | 100.0% | 100.0% | 0.0000 | 2487.9 | 0.1257s | - | 1 | 9 | 10 |
| 3 | GEP_3 | GEP | 8/8 | 100.0% | 87.5% | 0.0125 | 1835.9 | 0.0635s | 3 | 3 | 4 | 5 |
| 4 | h4 | Original | 8/8 | 100.0% | 75.0% | 0.0155 | 1810.4 | 0.1079s | - | 4 | 2 | 8 |
| 5 | GP_3 | GP | 8/8 | 100.0% | 75.0% | 0.0179 | 1769.1 | 0.0657s | 7 | 5 | 1 | 6 |
| 6 | h5 | Original | 8/8 | 100.0% | 62.5% | 0.0280 | 1821.8 | 0.0976s | - | 6 | 3 | 7 |
| 7 | h2 | Original | 8/8 | 100.0% | 37.5% | 0.0469 | 2196.5 | 0.1245s | - | 7 | 7 | 9 |
| 8 | GEP_1 | GEP | 8/8 | 100.0% | 25.0% | 0.0787 | 2570.5 | 0.0253s | 4 | 8 | 10 | 1 |
| 9 | GEP_2 | GEP | 8/8 | 100.0% | 25.0% | 0.0787 | 2570.5 | 0.0292s | 3 | 8 | 10 | 2 |
| 10 | GP_2 | GP | 8/8 | 100.0% | 25.0% | 0.0833 | 1940.2 | 0.0359s | 5 | 10 | 5 | 3 |
| 11 | GP_1 | GP | 8/8 | 100.0% | 25.0% | 0.0833 | 1943.4 | 0.0418s | 3 | 10 | 6 | 4 |

## Interpretation

- Every heuristic receives the same wall-clock time limit on every final benchmark puzzle.
- Overall rank is lexicographic: success rate first, then solution gap, expanded nodes, and runtime.
- Expanded nodes are the primary stable measure of A* guidance; runtime is reported as the median of repeated runs.
- Generated-heuristic complexity is the number of active expression operators. Inactive GEP tail symbols are not counted.
- GP and GEP are evolved independently with multiple random seeds; seed-level outcomes are available in the seed-summary CSV files.
- Structural and behavioral diversity histories, per-puzzle values, and all-40-puzzle summaries are available in the accompanying CSV files.
