"""A linked LIFO stack with constant-time push and pop."""


class _Node:
    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node


class Stack:
    def __init__(self):
        self._top = None
        self._size = 0

    def push(self, value):
        self._top = _Node(value, self._top)
        self._size += 1

    def pop(self):
        if self._top is None:
            raise IndexError("pop from empty stack")
        value = self._top.value
        self._top = self._top.next
        self._size -= 1
        return value

    def peek(self):
        if self._top is None:
            raise IndexError("peek from empty stack")
        return self._top.value

    def is_empty(self):
        return self._size == 0

    def size(self):
        return self._size
