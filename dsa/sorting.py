"""Sorting algorithms used by the ThreadVault project."""


def merge_sort(values, key=lambda value: value):
    if len(values) < 2:
        return list(values)

    middle = len(values) // 2
    left = merge_sort(values[:middle], key)
    right = merge_sort(values[middle:], key)
    result = []
    left_index = right_index = 0

    while left_index < len(left) and right_index < len(right):
        if key(left[left_index]) <= key(right[right_index]):
            result.append(left[left_index])
            left_index += 1
        else:
            result.append(right[right_index])
            right_index += 1

    result.extend(left[left_index:])
    result.extend(right[right_index:])
    return result


def insertion_sort(values, key=lambda value: value):
    result = list(values)
    for index in range(1, len(result)):
        current = result[index]
        cursor = index - 1
        while cursor >= 0 and key(result[cursor]) > key(current):
            result[cursor + 1] = result[cursor]
            cursor -= 1
        result[cursor + 1] = current
    return result
