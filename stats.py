
#Computes the average (mean) of a list of values.
def average(values):
    if not values:
        return None
    return sum(values) / len(values)


#Returns basic statistics for search depths.
def calculate_depth_stats(depths, leaves_depths=None):
    if not depths:
        return None, None, None

    # The requirement defines MIN as the shallowest depth reached
    # before a branch was cut off or ended.
    # If you track leaf node depths separately, use those for the min.
    # Otherwise, we use the depths list provided.

    current_min = min(leaves_depths) if leaves_depths else min(depths)
    current_avg = sum(depths) / len(depths)
    current_max = max(depths)

    return current_min, current_avg, current_max


# Approximates the Effective Branching Factor (EBF).
#The EBF is defined by the equation: N = 1 + b + b^2 + ... + b^d
# where:
#N is the total number of nodes generated
#d is the depth of the solution
#b is the branching factor (unknown)
def compute_ebf(N, d, eps=1e-7):
    #Computes the geometric series:
    # 1 + b + b^2 + ... + b^depth
    if d is None or d <= 0 or N <= 1:
        return None

    low = 1.0
    high = max(2.0, float(N))

    def series_sum(b, depth):
        total = 0.0
        for i in range(depth + 1):
            total += b ** i
        return total

    for _ in range(100):
        mid = (low + high) / 2
        value = series_sum(mid, d)

        if abs(value - N) < eps:
            return mid

        if value < N:
            low = mid
        else:
            high = mid

    return (low + high) / 2