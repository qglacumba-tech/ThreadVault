"""Linear and binary search algorithms."""


def linear_search(values, predicate):
    for index, value in enumerate(values):
        if predicate(value):
            return index
    return -1


def linear_search_all(values, predicate):
    matches = []
    for value in values:
        if predicate(value):
            matches.append(value)
    return matches


def binary_search(values, target, key=lambda value: value):
    low, high = 0, len(values) - 1
    while low <= high:
        middle = (low + high) // 2
        current = key(values[middle])
        if current == target:
            return middle
        if current < target:
            low = middle + 1
        else:
            high = middle - 1
    return -1
