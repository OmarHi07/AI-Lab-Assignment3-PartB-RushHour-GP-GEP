"""Cached numeric Rush Hour features used as GP/GEP terminals."""

from functools import lru_cache

from moves import get_successors
from state import BOARD_SIZE, get_cars, str_to_board


TERMINAL_NAMES = ("D", "B", "S", "K", "M", "C", "V", "L")

TERMINAL_DESCRIPTIONS = {
    "D": "cells from the right side of X to the exit",
    "B": "unique vehicles directly blocking X",
    "S": "unique secondary vehicles blocking a direct blocker",
    "K": "direct blockers that cannot immediately clear the exit row",
    "M": "available directions that immediately clear direct blockers",
    "C": "minimum total blocker-clearance distance in cells",
    "V": "total number of vehicles on the board",
    "L": "number of legal successor moves from the state",
}


def _unique_direct_blockers(board, row_x, rightmost_x):
    blockers = []
    for column in range(rightmost_x + 1, BOARD_SIZE):
        car = board[row_x][column]
        if car != "." and car not in blockers:
            blockers.append(car)
    return blockers


def _path_information(board, cells, row_x):
    """Return feasible clearing directions, cost, and secondary blockers."""
    column = cells[0][1]
    topmost = min(row for row, _ in cells)
    bottommost = max(row for row, _ in cells)

    up_steps = bottommost - row_x + 1
    down_steps = row_x - topmost + 1
    options = []
    secondary = set()

    if topmost - up_steps >= 0:
        path = [board[topmost - step][column] for step in range(1, up_steps + 1)]
        obstacles = {car for car in path if car != "."}
        secondary.update(obstacles)
        if not obstacles:
            options.append(up_steps)

    if bottommost + down_steps < BOARD_SIZE:
        path = [board[bottommost + step][column] for step in range(1, down_steps + 1)]
        obstacles = {car for car in path if car != "."}
        secondary.update(obstacles)
        if not obstacles:
            options.append(down_steps)

    fallback_cost = min(up_steps, down_steps)
    return options, fallback_cost, secondary


@lru_cache(maxsize=200_000)
def extract_features(state):
    """Extract the terminal values for one immutable 36-character state."""
    board = str_to_board(state)
    cars = get_cars(board)
    x_cells = cars["X"]["cells"]
    row_x = x_cells[0][0]
    rightmost_x = max(column for _, column in x_cells)
    direct_blockers = _unique_direct_blockers(board, row_x, rightmost_x)

    secondary_blockers = set()
    blocked_count = 0
    clearing_directions = 0
    clearance_cost = 0

    for car in direct_blockers:
        info = cars[car]
        if info["direction"] != "V":
            blocked_count += 1
            clearance_cost += 1
            continue

        options, fallback_cost, secondary = _path_information(
            board, info["cells"], row_x
        )
        secondary.discard(car)
        secondary.discard("X")
        secondary_blockers.update(secondary)
        clearing_directions += len(options)

        if options:
            clearance_cost += min(options)
        else:
            blocked_count += 1
            clearance_cost += fallback_cost

    return {
        "D": float((BOARD_SIZE - 1) - rightmost_x),
        "B": float(len(direct_blockers)),
        "S": float(len(secondary_blockers)),
        "K": float(blocked_count),
        "M": float(clearing_directions),
        "C": float(clearance_cost),
        "V": float(len(cars)),
        "L": float(len(get_successors(state))),
    }


def clear_feature_cache():
    extract_features.cache_clear()
