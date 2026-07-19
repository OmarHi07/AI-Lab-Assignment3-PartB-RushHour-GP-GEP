
from state import str_to_board, get_cars, BOARD_SIZE

# First heuristic:
# Counts the number of vehicles blocking X on its way to the exit.
def h1(state):
    board = str_to_board(state)
    cars = get_cars(board)

    x_cells = cars['X']['cells']
    row = x_cells[0][0]
    rightmost = max(c for r, c in x_cells)

    blockers = set()

    for c in range(rightmost + 1, BOARD_SIZE):
        if board[row][c] != '.':
            blockers.add(board[row][c])

    return len(blockers)


#Second heuristic:
#Distance of X from the exit plus the number of blocking vehicles.
def h2(state):
    board = str_to_board(state)
    cars = get_cars(board)

    x_cells = cars['X']['cells']
    rightmost = max(c for r, c in x_cells)

    distance_to_exit = (BOARD_SIZE - 1) - rightmost
    blockers = h1(state)

    return distance_to_exit + blockers


from state import str_to_board, get_cars, BOARD_SIZE


def h4(state):
    """
    Heuristic function (h4) for Rush Hour.
    Calculates the estimated cost to reach the goal based on vehicles
    blocking the target car 'X' and the effort required to move those blockers.
    """
    board = str_to_board(state)
    cars = get_cars(board)

    # Identify the target car 'X' and its position on the exit row
    x_cells = cars['X']['cells']
    row_x = x_cells[0][0]
    rightmost_x = max(c for r, c in x_cells)

    # Identify all unique vehicles currently blocking car 'X' from the exit
    blockers = []
    for c in range(rightmost_x + 1, BOARD_SIZE):
        ch = board[row_x][c]
        if ch != '.' and ch not in blockers:
            blockers.append(ch)

    # Initial score is the number of direct blocking vehicles
    score = len(blockers)

    for car in blockers:
        info = cars[car]
        cells = info['cells']
        direction = info['direction']

        # If for some reason the blocker isn't vertical, apply a minor penalty
        # Most blockers in Rush Hour are vertical relative to the exit row.
        if direction != 'V':
            score += 1
            continue

        col = cells[0][1]
        topmost = min(r for r, c in cells)
        bottommost = max(r for r, c in cells)

        # Calculate how many cells of the blocking car occupy the exit row
        rows_of_car = [r for r, c in cells]
        overlap_on_exit_row = sum(1 for r in rows_of_car if r == row_x)

        # Usually, a vertical blocker occupies 1 cell on the exit row,
        # requiring at least 1 move to clear the path.
        steps_needed = overlap_on_exit_row if overlap_on_exit_row > 0 else 1

        # Check if the blocker can move UP to clear the exit row
        can_up = True
        for step in range(1, steps_needed + 1):
            if topmost - step < 0 or board[topmost - step][col] != '.':
                can_up = False
                break

        # Check if the blocker can move DOWN to clear the exit row
        can_down = True
        for step in range(1, steps_needed + 1):
            if bottommost + step >= BOARD_SIZE or board[bottommost + step][col] != '.':
                can_down = False
                break

        # If the blocker can be moved immediately in at least one direction,
        # add the necessary steps to the score.
        if can_up or can_down:
            score += steps_needed
        else:
            # If the blocker is itself blocked and cannot move immediately,
            # apply a higher penalty to reflect the increased complexity.
            score += steps_needed + 2

    return score

from state import str_to_board, get_cars, BOARD_SIZE


def h_admissible(state):
    """
    Heuristic admissible:
    counts direct blockers of X,
    and adds only unavoidable extra cost
    when a blocking vertical car cannot move immediately.
    """
    board = str_to_board(state)
    cars = get_cars(board)

    x_cells = cars['X']['cells']
    row_x = x_cells[0][0]
    rightmost_x = max(c for r, c in x_cells)

    blockers = []
    for c in range(rightmost_x + 1, BOARD_SIZE):
        ch = board[row_x][c]
        if ch != '.' and ch not in blockers:
            blockers.append(ch)

    score = len(blockers)

    for car in blockers:
        info = cars[car]
        cells = info['cells']
        direction = info['direction']

        if direction == 'V':
            col = cells[0][1]
            topmost = min(r for r, c in cells)
            bottommost = max(r for r, c in cells)

            can_move_up = topmost - 1 >= 0 and board[topmost - 1][col] == '.'
            can_move_down = bottommost + 1 < BOARD_SIZE and board[bottommost + 1][col] == '.'


            if not can_move_up and not can_move_down:
                score += 1

    return score

from state import str_to_board, get_cars, BOARD_SIZE


def h5(state):
    """
    Heuristic function (h5) for Rush Hour.
    An advanced blocking-car heuristic that accounts for secondary blockers
    (cars that block the blockers themselves).
    """
    board = str_to_board(state)
    cars = get_cars(board)

    # Identify the target car 'X' and its position on the exit row
    x_cells = cars['X']['cells']
    row_x = x_cells[0][0]
    rightmost_x = max(c for r, c in x_cells)

    # Find all unique vehicles blocking 'X' from the exit
    blockers = []
    for c in range(rightmost_x + 1, BOARD_SIZE):
        ch = board[row_x][c]
        if ch != '.' and ch not in blockers:
            blockers.append(ch)

    # The base score is the number of direct blockers
    score = len(blockers)

    for car in blockers:
        info = cars[car]
        cells = info['cells']
        direction = info['direction']

        # If the blocker is not vertical, it shouldn't be on the exit row
        # in a standard puzzle, but we apply a small penalty just in case.
        if direction != 'V':
            score += 1
            continue

        col = cells[0][1]
        topmost = min(r for r, c in cells)
        bottommost = max(r for r, c in cells)

        # Check if the vertical blocker has immediate room to move at least one step
        can_move_up = topmost - 1 >= 0 and board[topmost - 1][col] == '.'
        can_move_down = bottommost + 1 < BOARD_SIZE and board[bottommost + 1][col] == '.'

        if can_move_up or can_move_down:
            # If it can move, we only add a small cost
            score += 1
        else:
            # If the blocker is "stuck" (cannot move up or down), increase the cost
            score += 2
            # Check for secondary blockers above
            if topmost - 1 >= 0:
                up_cell = board[topmost - 1][col]
                # If there is another car blocking the blocker's path upward
                if up_cell != '.' and up_cell != car:
                    score += 1

            # Check for secondary blockers below
            if bottommost + 1 < BOARD_SIZE:
                down_cell = board[bottommost + 1][col]
                # If there is another car blocking the blocker's path downward
                if down_cell != '.' and down_cell != car:
                    score += 1
    return score