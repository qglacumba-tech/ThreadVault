"""Seller fulfillment ordering and status-history selection."""

from typing import Any

from dsa.priority_queue import PriorityQueue
from dsa.stack import Stack


PRIORITY_RANK = {"urgent": 1, "express": 2, "standard": 3}


def order_work_list(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order seller work by priority, then order id and item id."""
    queue = PriorityQueue()
    for row in rows:
        queue.insert(
            row,
            (PRIORITY_RANK[row["priority"]], row["order_id"], row["item_id"]),
        )

    ordered = []
    while not queue.is_empty():
        ordered.append(queue.extract_min())
    return ordered


def latest_undoable(history_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest eligible history row from rows ordered by ascending id."""
    stack = Stack()
    for event in history_rows:
        stack.push(event)
    if stack.is_empty():
        return None
    return stack.pop()
