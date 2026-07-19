
def clean_line(line):
    return line.strip()

def load_puzzles(filename):
    puzzles = []
    inside_input_block = False

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = clean_line(line)

            if line == "--- RH-input ---":
                inside_input_block = True
                continue

            if line == "--- end RH-input ---":
                break

            if inside_input_block and len(line) == 36:
                puzzles.append(line)

    return puzzles