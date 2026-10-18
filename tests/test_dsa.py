import pytest

from dsa.priority_queue import PriorityQueue
from dsa.queue import Queue
from dsa.searching import binary_search, linear_search
from dsa.sorting import insertion_sort, merge_sort
from dsa.stack import Stack


def test_queue_is_fifo_and_tracks_size():
    queue = Queue()
    queue.enqueue("A")
    queue.enqueue("B")
    assert queue.peek() == "A"
    assert queue.size() == 2
    assert queue.dequeue() == "A"
    assert queue.dequeue() == "B"
    assert queue.is_empty()
    with pytest.raises(IndexError):
        queue.dequeue()


def test_stack_is_lifo_and_tracks_size():
    stack = Stack()
    stack.push("first")
    stack.push("last")
    assert stack.peek() == "last"
    assert stack.pop() == "last"
    assert stack.pop() == "first"
    assert stack.size() == 0
    with pytest.raises(IndexError):
        stack.pop()


def test_priority_queue_orders_priority_then_arrival():
    queue = PriorityQueue()
    queue.insert("standard", 3)
    queue.insert("urgent one", 1)
    queue.insert("urgent two", 1)
    assert [queue.extract_min(), queue.extract_min(), queue.extract_min()] == [
        "urgent one", "urgent two", "standard"
    ]


def test_sorts_match_expected_order_and_preserve_equal_key_order():
    values = [(2, "first two"), (1, "one"), (2, "second two")]
    expected = [(1, "one"), (2, "first two"), (2, "second two")]
    assert merge_sort(values, key=lambda item: item[0]) == expected
    assert insertion_sort(values, key=lambda item: item[0]) == expected


def test_searches_find_values_or_return_minus_one():
    values = [1, 3, 5, 7]
    assert linear_search(values, lambda value: value == 5) == 2
    assert linear_search(values, lambda value: value == 4) == -1
    assert binary_search(values, 7) == 3
    assert binary_search(values, 4) == -1
