from services.catalog import search_catalog, sort_catalog
from services.fulfillment import latest_undoable, order_work_list
from services.ordering import order_lines_in_sequence


def test_checkout_lines_are_returned_in_fifo_order():
    lines = [(8, "M", 1), (3, "L", 2), (8, "S", 1)]

    assert order_lines_in_sequence(lines) == lines


def test_seller_work_orders_priority_then_order_and_item_ids():
    rows = [
        {"priority": "standard", "order_id": 1, "item_id": 4},
        {"priority": "urgent", "order_id": 9, "item_id": 2},
        {"priority": "urgent", "order_id": 3, "item_id": 8},
        {"priority": "express", "order_id": 2, "item_id": 1},
        {"priority": "urgent", "order_id": 3, "item_id": 2},
    ]

    ordered = order_work_list(rows)

    assert [(row["priority"], row["order_id"], row["item_id"]) for row in ordered] == [
        ("urgent", 3, 2),
        ("urgent", 3, 8),
        ("urgent", 9, 2),
        ("express", 2, 1),
        ("standard", 1, 4),
    ]
    assert rows[0]["priority"] == "standard"


def test_latest_undoable_uses_last_history_row_and_handles_empty_history():
    history = [
        {"id": 10, "old_status": "pending", "new_status": "processing"},
        {"id": 11, "old_status": "processing", "new_status": "fulfilled"},
    ]

    assert latest_undoable(history) == history[-1]
    assert latest_undoable([]) is None


def test_catalog_search_matches_brand_name_or_category_case_insensitively():
    products = [
        {"brand": "ThreadVault", "name": "Ribbed Tee", "category": "Tees"},
        {"brand": "Other", "name": "Canvas Bag", "category": "Accessories"},
    ]

    assert search_catalog(products, "  RIBBED ") == [products[0]]
    assert search_catalog(products, "accessories") == [products[1]]
    assert search_catalog(products, "missing") == []
    assert search_catalog(products, "  ") == products


def test_catalog_sort_orders_names_without_mutating_input():
    products = [
        {"name": "thread tee"},
        {"name": "Jacket"},
        {"name": "Cap"},
    ]

    assert sort_catalog(products) == [
        {"name": "Cap"},
        {"name": "Jacket"},
        {"name": "thread tee"},
    ]
    assert products[0]["name"] == "thread tee"
