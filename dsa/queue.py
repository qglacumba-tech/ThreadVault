"""A linked FIFO queue with constant-time enqueue and dequeue."""

from __future__ import annotations


class _Node:
    def __init__(self, value):
        self.value = value
        self.next: _Node | None = None


class Queue:
    def __init__(self):
        self._head = None
        self._tail = None
        self._size = 0

    def enqueue(self, value):
        node = _Node(value)
        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            self._tail = node
        self._size += 1

    def dequeue(self):
        if self._head is None:
            raise IndexError("dequeue from empty queue")
        value = self._head.value
        self._head = self._head.next
        self._size -= 1
        if self._head is None:
            self._tail = None
        return value

    def peek(self):
        if self._head is None:
            raise IndexError("peek from empty queue")
        return self._head.value

    def is_empty(self):
        return self._size == 0

    def size(self):
        return self._size
