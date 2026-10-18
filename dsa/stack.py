"""A linked LIFO stack with constant-time push and pop."""


class _Node:
    """One value and the link to the next node below it."""

    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node


class Stack:
    """LIFO stack backed by linked nodes.

    Invariant: the top node is the most recently pushed value, and size is
    the number of nodes reachable from the top.
    """

    def __init__(self):
        self._top = None
        self._size = 0

    def push(self, value):
        """Add a value at the top in O(1) time."""
        self._top = _Node(value, self._top)
        self._size += 1

    def pop(self):
        """Remove and return the top value in O(1) time."""
        if self._top is None:
            raise IndexError("pop from empty stack")
        value = self._top.value
        self._top = self._top.next
        self._size -= 1
        return value

    def peek(self):
        """Return the top value without removing it, in O(1) time."""
        if self._top is None:
            raise IndexError("peek from empty stack")
        return self._top.value

    def is_empty(self):
        """Return whether the stack contains no values, in O(1) time."""
        return self._size == 0

    def size(self):
        """Return the number of values in O(1) time."""
        return self._size
