
from collections import deque
import heapq
import time

from moves import get_successors
from state import str_to_board, get_cars
from stats import average, calculate_depth_stats

def is_goal(state):
   # Goal state:
   # The car 'X' is horizontal, and its rightmost cell is in column 5 (exit).
    cars = get_cars(str_to_board(state))
    x_cells = cars['X']['cells']
    rightmost = max(c for r, c in x_cells)
    return rightmost == 5

def reconstruct_path(parent_map, end_state):
    #Reconstructs the sequence of moves from the start state to the goal state.

    #Parameters:
    # parent_map: dictionary mapping each state to (parent_state, move)
    # end_state: the goal state


    moves = []
    current = end_state

    while parent_map[current] is not None:
        parent_state, move = parent_map[current]
        moves.append(move)
        current = parent_state

    moves.reverse()
    #Returns:
    # List of moves from start to goal
    return moves

def bfs(start_state, time_limit_seconds=10):
    #Breadth-First Search (BFS) – uninformed baseline search.
    #Parameters:
    # start_state: initial state of the puzzle
    # time_limit_seconds: maximum allowed runtime

    #Process:
    # Uses a queue (FIFO) to explore states level by level
    # Tracks visited states to avoid repetitions
    # Stores parent relationships to reconstruct the solution
    # Tracks statistics such as:
    #   * number of expanded nodes
    #   * depth information

    #Returns:
    # Dictionary with:
    #    success: whether a solution was found
    #    solution: list of moves (if found)
    #   solution_length: number of moves
    #   nodes_expanded: total nodes expanded
    #   time_ms: runtime in milliseconds
    #   avg_h: None (no heuristic in BFS)
    #   min_depth / avg_depth / max_depth: depth statistics
    start_time = time.time()

    queue = deque([start_state])
    visited = {start_state}
    parent_map = {start_state: None}
    depth_map = {start_state: 0}

    nodes_expanded = 0
    depths_seen = []
    leaves_depths = []

    while queue:
        # Time limit check
        if time.time() - start_time > time_limit_seconds:
            min_d, avg_d, max_d = calculate_depth_stats(depths_seen,leaves_depths)
            return {
                "success": False,
                "solution": None,
                "solution_length": None,
                "nodes_expanded": nodes_expanded,
                "time_ms": int((time.time() - start_time) * 1000),
                "avg_h": None,
                "min_depth": min_d,
                "avg_depth": avg_d,
                "max_depth": max_d,
            }

        state = queue.popleft()
        current_depth = depth_map[state]
        depths_seen.append(current_depth)
        nodes_expanded += 1

        if is_goal(state):
            solution = reconstruct_path(parent_map, state)
            min_d, avg_d, max_d = calculate_depth_stats(depths_seen,leaves_depths)
            return {
                "success": True,
                "solution": solution,
                "solution_length": len(solution),
                "nodes_expanded": nodes_expanded,
                "time_ms": int((time.time() - start_time) * 1000),
                "avg_h": None,
                "min_depth": min_d,
                "avg_depth": avg_d,
                "max_depth": max_d,
            }


        added_any = False

        for next_state, move in get_successors(state):
            if next_state not in visited:
                visited.add(next_state)
                parent_map[next_state] = (state, move)
                depth_map[next_state] = current_depth + 1
                queue.append(next_state)
                added_any = True

        # If no new states were added, this branch "ended" here
        if not added_any:
            leaves_depths.append(current_depth)

    min_d, avg_d, max_d = calculate_depth_stats(depths_seen, leaves_depths)
    return {
        "success": False,
        "solution": None,
        "solution_length": None,
        "nodes_expanded": nodes_expanded,
        "time_ms": int((time.time() - start_time) * 1000),
        "avg_h": None,
        "min_depth": min_d,
        "avg_depth": avg_d,
        "max_depth": max_d,
    }

def astar(start_state, heuristic, time_limit_seconds=10, node_limit=None):
    """Run A* with a supplied ``h(state)`` function.

    ``node_limit`` is optional and is especially useful during GP/GEP fitness
    evaluation. Unlike very short wall-clock limits, a node budget is stable
    and gives every evolved individual the same search allowance.
    """
    start_time = time.perf_counter()
    open_heap = []
    heuristic_evaluations = 0

    def evaluate_heuristic(state):
        nonlocal heuristic_evaluations
        heuristic_evaluations += 1
        return heuristic(state)

    start_h = evaluate_heuristic(start_state)
    heapq.heappush(open_heap, (start_h, 0, start_state))

    g_score = {start_state: 0}
    parent_map = {start_state: None}
    nodes_expanded = 0
    nodes_generated = 1
    heuristic_values = []
    depths_seen = []
    leaves_depths = []

    def make_result(success, solution, termination_reason):
        elapsed = time.perf_counter() - start_time
        min_d, avg_d, max_d = calculate_depth_stats(depths_seen, leaves_depths)
        return {
            "success": success,
            "solution": solution,
            "solution_length": len(solution) if solution is not None else None,
            "nodes_expanded": nodes_expanded,
            "nodes_generated": nodes_generated,
            "heuristic_evaluations": heuristic_evaluations,
            "time_ms": int(elapsed * 1000),
            "time_seconds": elapsed,
            "avg_h": average(heuristic_values),
            "min_depth": min_d,
            "avg_depth": avg_d,
            "max_depth": max_d,
            "termination_reason": termination_reason,
        }

    while open_heap:
        elapsed = time.perf_counter() - start_time
        if time_limit_seconds is not None and elapsed > time_limit_seconds:
            return make_result(False, None, "time_limit")
        if node_limit is not None and nodes_expanded >= node_limit:
            return make_result(False, None, "node_limit")

        _, g, state = heapq.heappop(open_heap)

        if g != g_score.get(state, float("inf")):
            continue

        nodes_expanded += 1
        depths_seen.append(g)

        h_val = evaluate_heuristic(state)
        heuristic_values.append(h_val)

        if is_goal(state):
            solution = reconstruct_path(parent_map, state)
            return make_result(True, solution, "goal")

        added_any = False

        for next_state, move in get_successors(state):
            new_g = g + 1

            if new_g < g_score.get(next_state, float("inf")):
                g_score[next_state] = new_g
                parent_map[next_state] = (state, move)
                new_f = new_g + evaluate_heuristic(next_state)
                heapq.heappush(open_heap, (new_f, new_g, next_state))
                nodes_generated += 1
                added_any = True

        if not added_any:
            leaves_depths.append(g)

    return make_result(False, None, "exhausted")
