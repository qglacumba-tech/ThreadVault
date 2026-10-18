"""Checkout line-item ordering workflow."""

from collections.abc import Sequence

from dsa.queue import Queue


CheckoutLine = tuple[int, str, int]


def order_lines_in_sequence(lines: Sequence[CheckoutLine]) -> list[CheckoutLine]:
    """Return validated checkout lines in FIFO insertion order."""
    queue = Queue()
    for line in lines:
        queue.enqueue(line)

    ordered = []
    while not queue.is_empty():
        ordered.append(queue.dequeue())
    return ordered
