import os
import uuid

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("THREADVAULT_RUN_DB_TESTS") != "1",
    reason="Set THREADVAULT_RUN_DB_TESTS=1 to run against a disposable MariaDB test database.",
)


def response_json(response):
    data = response.json
    assert data is not None
    return data


def test_seller_customer_order_fulfillment_and_undo():
    from app import app

    app.config.update(TESTING=True, SECRET_KEY="integration-test-key")
    client = app.test_client()
    suffix = uuid.uuid4().hex
    seller_email = f"seller-{suffix}@example.test"
    customer_email = f"customer-{suffix}@example.test"

    response = client.post("/api/auth/register", json={
        "email": seller_email,
        "password": "test-password-123",
        "role": "seller",
        "display_name": "Test Seller",
        "shop_name": f"Test Shop {suffix[:8]}",
    })
    assert response.status_code == 201

    response = client.post("/api/seller/products", json={
        "name": "Test Shirt",
        "category": "Tees",
        "description": "Integration test listing",
        "price": "500.00",
        "image_url": "/assets/IMG_5474.PNG",
        "stock": [{"size": "M", "quantity": 3}],
    })
    assert response.status_code == 201
    product_id = response_json(response)["id"]

    response = client.post("/api/auth/logout", json={})
    assert response.status_code == 200
    response = client.post("/api/auth/register", json={
        "email": customer_email,
        "password": "test-password-123",
        "role": "customer",
        "display_name": "Test Customer",
    })
    assert response.status_code == 201

    response = client.post("/api/orders", json={
        "priority": "urgent",
        "items": [{"product_id": product_id, "size": "M", "quantity": 2}],
    })
    assert response.status_code == 201
    order_id = response_json(response)["order_id"]

    failed_order = client.post("/api/orders", json={
        "items": [{"product_id": product_id, "size": "M", "quantity": 2}],
    })
    assert failed_order.status_code == 409
    assert len(response_json(client.get("/api/orders"))) == 1
    catalog = response_json(client.get("/api/products"))
    storefront_product = next(
        product for product in catalog
        if product["id"] == product_id
    )
    assert storefront_product["stock"]["M"] == 1

    client.post("/api/auth/logout", json={})
    response = client.post("/api/auth/login", json={
        "email": seller_email,
        "password": "test-password-123",
    })
    assert response.status_code == 200
    seller_items = response_json(client.get("/api/seller/orders"))
    assert len(seller_items) == 1
    assert seller_items[0]["order_id"] == order_id
    item_id = seller_items[0]["item_id"]

    assert client.patch(
        f"/api/seller/order-items/{item_id}", json={"status": "processing"}
    ).status_code == 200
    assert client.patch(
        f"/api/seller/order-items/{item_id}", json={"status": "fulfilled"}
    ).status_code == 200
    assert response_json(client.post("/api/seller/orders/undo-last-status", json={})).get(
        "restored_status"
    ) == "processing"
    assert response_json(client.post("/api/seller/orders/undo-last-status", json={})).get(
        "restored_status"
    ) == "pending"

    client.post("/api/auth/logout", json={})
    other_seller = client.post("/api/auth/register", json={
        "email": f"other-{suffix}@example.test",
        "password": "test-password-123",
        "role": "seller",
        "display_name": "Other Seller",
        "shop_name": "Other Shop",
    })
    assert other_seller.status_code == 201
    assert client.put(f"/api/seller/products/{product_id}", json={
        "name": "Unauthorized edit",
        "category": "Tees",
        "description": "",
        "price": "1",
        "stock": [{"size": "M", "quantity": 1}],
    }).status_code == 404
