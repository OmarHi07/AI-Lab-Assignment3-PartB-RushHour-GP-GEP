from parser import load_puzzles
from search import bfs, astar, is_goal
from heuristics import h1, h2, h4, h_admissible, h5
from stats import compute_ebf
from state import print_board
from moves import get_successors


def run_single(problem_id, puzzle, time_limit=10):
    print("=" * 60)
    print(f"Problem {problem_id}")
    print("Initial board:")
    print_board(puzzle)

    results = []

    # BFS
    bfs_result = bfs(puzzle, time_limit_seconds=time_limit)
    bfs_result["problem"] = problem_id
    bfs_result["algorithm"] = "BFS"
    bfs_result["heuristic_name"] = "-"
    bfs_result["ebf"] = compute_ebf(
        bfs_result["nodes_expanded"],
        bfs_result["solution_length"]
    )
    results.append(bfs_result)

    # A* + h1
    a1_result = astar(puzzle, h1, time_limit_seconds=time_limit)
    a1_result["problem"] = problem_id
    a1_result["algorithm"] = "A*"
    a1_result["heuristic_name"] = "h1_blockers"
    a1_result["ebf"] = compute_ebf(
        a1_result["nodes_expanded"],
        a1_result["solution_length"]
    )
    results.append(a1_result)

    # A* + h2
    a2_result = astar(puzzle, h2, time_limit_seconds=time_limit)
    a2_result["problem"] = problem_id
    a2_result["algorithm"] = "A*"
    a2_result["heuristic_name"] = "h2_distance_plus_blockers"
    a2_result["ebf"] = compute_ebf(
        a2_result["nodes_expanded"],
        a2_result["solution_length"]
    )
    results.append(a2_result)

    a4_result = astar(puzzle, h4, time_limit_seconds=time_limit)
    a4_result["problem"] = problem_id
    a4_result["algorithm"] = "A*"
    a4_result["heuristic_name"] = "h4_blockers_plus_clear_cost"
    a4_result["ebf"] = compute_ebf(
        a4_result["nodes_expanded"],
        a4_result["solution_length"]
    )
    results.append(a4_result)

    a_adm_result = astar(puzzle, h_admissible, time_limit_seconds=time_limit)
    a_adm_result["problem"] = problem_id
    a_adm_result["algorithm"] = "A*"
    a_adm_result["heuristic_name"] = "h_admissible"
    a_adm_result["ebf"] = compute_ebf(
        a_adm_result["nodes_expanded"],
        a_adm_result["solution_length"]
    )
    results.append(a_adm_result)
    a5_result = astar(puzzle, h5, time_limit_seconds=time_limit)
    a5_result["problem"] = problem_id
    a5_result["algorithm"] = "A*"
    a5_result["heuristic_name"] = "h5_blockers_secondary"
    a5_result["ebf"] = compute_ebf(
        a5_result["nodes_expanded"],
        a5_result["solution_length"]
    )
    results.append(a5_result)
    return results

def print_results(results):
    print("\n" + "=" * 120)
    print("Problem | Heuristic name | N | d/N | Success (Y/N) | Time (ms) | EBF | avg H value | Min | Avg | Max")
    print("=" * 120)

    for r in results:
        success = "Y" if r["success"] else "N"
        d = r["solution_length"]
        N = r["nodes_expanded"]

        if d is not None and N > 0:
            d_over_N = f"{d / N:.6f}"
        else:
            d_over_N = "-"

        time_ms = r["time_ms"]
        ebf = f"{r['ebf']:.3f}" if r["ebf"] is not None else "-"
        avg_h = f"{r['avg_h']:.3f}" if r["avg_h"] is not None else "-"
        min_d = f"{r['min_depth']:.3f}" if r["min_depth"] is not None else "-"
        avg_d = f"{r['avg_depth']:.3f}" if r["avg_depth"] is not None else "-"
        max_d = f"{r['max_depth']:.3f}" if r["max_depth"] is not None else "-"

        print(
            f"{r['problem']:>7} | "
            f"{r['heuristic_name']:>24} | "
            f"{N:>5} | "
            f"{d_over_N:>8} | "
            f"{success:>13} | "
            f"{time_ms:>9} | "
            f"{ebf:>5} | "
            f"{avg_h:>11} | "
            f"{min_d:>4} | "
            f"{avg_d:>4} | "
            f"{max_d:>4}"
        )

def run_all(puzzles, time_limits):
    all_results = []

    for i, puzzle in enumerate(puzzles, start=1):
        current_limit = time_limits[i - 1]
        results = run_single(i, puzzle, time_limit=current_limit)
        all_results.extend(results)

    return all_results


def apply_solution(start_state, solution):
    current = start_state

    for move in solution:
        found = False

        for next_state, legal_move in get_successors(current):
            if legal_move == move:
                current = next_state
                found = True
                break

        if not found:
            raise ValueError(f"Illegal move in solution: {move}")

    return current


def format_solution(solution):
    """Convert internal moves such as ``3CL`` to the required ``CL3`` form."""
    formatted = []

    for move in solution:
        digit_count = 0
        while digit_count < len(move) and move[digit_count].isdigit():
            digit_count += 1

        distance = move[:digit_count]
        car_and_direction = move[digit_count:]

        if not distance or len(car_and_direction) != 2:
            raise ValueError(f"Invalid internal move format: {move}")

        formatted.append(f"{car_and_direction}{distance}")

    return " ".join(formatted)


def print_all_solutions(results, puzzles, show_final_board=False):
    print("\n" + "=" * 120)
    print("ALL SOLUTIONS")
    print("=" * 120)

    for r in results:
        print(f"\nProblem {r['problem']} | {r['algorithm']} | {r['heuristic_name']}")

        if not r["success"]:
            print("Soln: FAILED .")
            continue

        print(f"Soln: {format_solution(r['solution'])} .")

        final_state = apply_solution(puzzles[r["problem"] - 1], r["solution"])

        if show_final_board:
            print("Goal reached?", is_goal(final_state))
            print("Final board:")
            print_board(final_state)


def main():
    # Load puzzles from file
    puzzles = load_puzzles("rh.txt")

    # Check if puzzles were successfully loaded
    if not puzzles:
        print("No puzzles were found in file")
        return

    # Print number of loaded puzzles
    print("Number of puzzles loaded:", len(puzzles))

    #custom time limits in milliseconds
    ms_limits = [
        70, 50, 100, 10, 40, 50, 180, 50, 40, 150,  # 1-10
        60, 60, 300, 350, 70, 200, 200, 85, 50, 30,  # 11-20
        20, 200, 100, 400, 700, 400, 300, 100, 400, 100,  # 21-30
        400, 80, 300, 400, 400, 200, 200, 400, 450, 300  # 31-40
    ]

    # Convert ms to seconds for the search functions
    time_limits_sec = [ms / 1000.0 for ms in ms_limits]

    # we Pass the list of limits to run_all
    all_results = run_all(puzzles, time_limits=time_limits_sec)

    # Print a summary table of all results
    print_results(all_results)

    # Print solutions in the exact assignment notation: "Soln: CL3 ... XR5 ."
    # Set show_final_board=True while debugging to also display final boards.
    print_all_solutions(all_results, puzzles, show_final_board=False)


if __name__ == "__main__":
    main()
