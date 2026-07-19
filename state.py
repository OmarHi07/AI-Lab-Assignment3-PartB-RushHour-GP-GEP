BOARD_SIZE = 6

def str_to_board(state_str):
    return [list(state_str[i * BOARD_SIZE:(i + 1) * BOARD_SIZE]) for i in range(BOARD_SIZE)]


def board_to_str(board):
    return ''.join(''.join(row) for row in board)


def print_board(state):
    if isinstance(state, str):
        board = str_to_board(state)
    else:
        board = state

    for row in board:
        print(' '.join(row))
    print()

def get_cars(board):
    positions = {}
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            ch = board[r][c]
            if ch != '.':
                positions.setdefault(ch, []).append((r, c))

    cars = {}
    for car, cells in positions.items():
        cells = sorted(cells)

        if len(cells) == 1:
            direction = 'H'
        else:
            if cells[0][0] == cells[1][0]:
                direction = 'H'
            else:
                direction = 'V'

        cars[car] = {
            'cells': cells,
            'direction': direction,
            'length': len(cells)
        }

    return cars