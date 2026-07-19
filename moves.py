# moves.py

from state import str_to_board, board_to_str, get_cars, BOARD_SIZE

# Moves a horizontal car left or right on the board.
def move_horizontal(board, car, cells, step, direction):

    new_board = [row[:] for row in board]

    for r, c in cells:
        new_board[r][c] = '.'

    if direction == 'L':
        for r, c in cells:
            new_board[r][c - step] = car
    else:  # 'R'
        for r, c in cells:
            new_board[r][c + step] = car

    return new_board

# Moves a vertical car up or down on the board.
def move_vertical(board, car, cells, step, direction):

    new_board = [row[:] for row in board]

    for r, c in cells:
        new_board[r][c] = '.'

    if direction == 'U':
        for r, c in cells:
            new_board[r - step][c] = car
    else:  # 'D'
        for r, c in cells:
            new_board[r + step][c] = car

    return new_board


def get_successors(state):
    board = str_to_board(state)
    cars = get_cars(board)
    successors = []

    for car, info in cars.items():
        cells = info['cells']
        direction = info['direction']

        #The vehicle is positioned horizontally.
        if direction == 'H':
            #In which row is the vehicle located from the start
            row = cells[0][0]
            #The maximum and the minimum in the columns.
            leftmost = min(c for r, c in cells)
            rightmost = max(c for r, c in cells)

            # Left
            step = 1
            # Continue moving left while:
            # 1. We are still inside the board boundaries
            # 2. The next cell to the left is empty
            while leftmost - step >= 0 and board[row][leftmost - step] == '.':
                # Create a new board after moving the car 'step' positions to the left
                new_board = move_horizontal(board, car, cells, step, 'L')
                # Convert the new board into a string representation (state)
                new_state = board_to_str(new_board)
                move = f"{step}{car}L"
                # Add the new state and the move to the successors list
                successors.append((new_state, move))
                step += 1

            # Right
            step = 1
            # Continue moving right while:
            # 1. We are inside the board boundaries
            # 2. The next cell to the right is empty
            while rightmost + step < BOARD_SIZE and board[row][rightmost + step] == '.':
                # Create a new board after moving the car 'step' positions to the right
                new_board = move_horizontal(board, car, cells, step, 'R')
                # Convert the new board into a string representation (state)
                new_state = board_to_str(new_board)
                move = f"{step}{car}R"
                # Add the new state and the move to the successors list
                successors.append((new_state, move))
                step += 1


        # This section handles vertical movement ('V') for a car.
        # The car can move up or down as long as the path is clear ('.').
        else:  # 'V'
            # Get the column of the car (all its cells share the same column)
            col = cells[0][1]
            # Find the topmost and bottommost positions of the car
            topmost = min(r for r, c in cells)
            bottommost = max(r for r, c in cells)

            # Move Up
            step = 1
            # Continue moving up while:
            # 1. We are still within the board boundaries
            # 2. The cell above is empty
            while topmost - step >= 0 and board[topmost - step][col] == '.':
                # Create a new board after moving the car 'step' positions upward
                new_board = move_vertical(board, car, cells, step, 'U')
                # Convert the new board into a string representation (state)
                new_state = board_to_str(new_board)
                move = f"{step}{car}U"
                # Add the new state and move to the successors list
                successors.append((new_state, move))
                step += 1

            # Move Down
            step = 1
            # Continue moving down while:
            # 1. We are within the board boundaries
            # 2. The cell below is empty
            while bottommost + step < BOARD_SIZE and board[bottommost + step][col] == '.':
                # Create a new board after moving the car 'step' positions downward
                new_board = move_vertical(board, car, cells, step, 'D')
                # Convert the new board into a string representation (state)
                new_state = board_to_str(new_board)
                move = f"{step}{car}D"
                # Add the new state and move to the successors list
                successors.append((new_state, move))
                step += 1

    return successors