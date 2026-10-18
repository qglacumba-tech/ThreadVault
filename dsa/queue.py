"""A linked FIFO queue with constant-time enqueue and dequeue."""

from __future__ import annotations


class _Node:
    """One value and the link to the next queue node."""

    def __init__(self, value):
        self.value = value
        self.next: _Node | None = None


class Queue:
    """FIFO queue backed by linked nodes.

    Invariant: an empty queue has no head or tail; a non-empty queue's head
    and tail are its first and last nodes, and the tail has no next node.
    """

    def __init__(self):
        self._head = None
        self._tail = None
        self._size = 0

    def enqueue(self, value):
        """Add a value at the tail in O(1) time."""
        node = _Node(value)
        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            self._tail = node
        self._size += 1

    def dequeue(self):
        """Remove and return the head value in O(1) time."""
        if self._head is None:
            raise IndexError("dequeue from empty queue")
        value = self._head.value
        self._head = self._head.next
        self._size -= 1
        if self._head is None:
            self._tail = None
        return value

    def peek(self):
        """Return the head value without removing it, in O(1) time."""
        if self._head is None:
            raise IndexError("peek from empty queue")
        return self._head.value

    def is_empty(self):
        """Return whether the queue contains no values, in O(1) time."""
        return self._size == 0

    def size(self):
        """Return the number of values in O(1) time."""
        return self._size
