"""Catalog search and ordering workflows."""

from typing import Any

from dsa.searching import linear_search_all
from dsa.sorting import merge_sort


def search_catalog(products: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Filter products by brand, name, or category using a case-insensitive query."""
    normalized_query = query.strip().casefold()
    if not normalized_query:
        return list(products)

    return linear_search_all(
        products,
        lambda product: normalized_query in (
            f'{product["brand"]} {product["name"]} {product["category"]}'
        ).casefold(),
    )


def sort_catalog(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return products ordered by case-insensitive name."""
    return merge_sort(products, key=lambda product: product["name"].casefold())
