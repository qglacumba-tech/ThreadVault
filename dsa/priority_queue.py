"""Stable binary min-heap priority queue."""


class PriorityQueue:
    def __init__(self):
        self._heap = []
        self._sequence = 0

    def insert(self, item, priority):
        entry = (priority, self._sequence, item)
        self._sequence += 1
        self._heap.append(entry)
        self._sift_up(len(self._heap) - 1)

    def peek(self):
        if not self._heap:
            raise IndexError("peek from empty priority queue")
        return self._heap[0][2]

    def extract_min(self):
        if not self._heap:
            raise IndexError("extract_min from empty priority queue")
        if len(self._heap) == 1:
            return self._heap.pop()[2]
        minimum = self._heap[0][2]
        self._heap[0] = self._heap.pop()
        self._sift_down(0)
        return minimum

    def is_empty(self):
        return not self._heap

    def size(self):
        return len(self._heap)

    def _sift_up(self, index):
        while index > 0:
            parent = (index - 1) // 2
            if self._heap[parent][:2] <= self._heap[index][:2]:
                break
            self._heap[parent], self._heap[index] = self._heap[index], self._heap[parent]
            index = parent

    def _sift_down(self, index):
        size = len(self._heap)
        while True:
            left = 2 * index + 1
            right = left + 1
            smallest = index
            if left < size and self._heap[left][:2] < self._heap[smallest][:2]:
                smallest = left
            if right < size and self._heap[right][:2] < self._heap[smallest][:2]:
                smallest = right
            if smallest == index:
                return
            self._heap[index], self._heap[smallest] = self._heap[smallest], self._heap[index]
            index = smallest
