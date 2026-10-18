"""ThreadVault storefront and local marketplace API."""

from decimal import Decimal, InvalidOperation
from functools import wraps
import json
import os
from pathlib import Path
import secrets
from typing import Any, cast
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error as MySQLError

from services.catalog import search_catalog, sort_catalog
from services.fulfillment import PRIORITY_RANK, latest_undoable, order_work_list
from services.ordering import CheckoutLine, order_lines_in_sequence


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
ASSETS = ROOT / "assets"
load_dotenv(ROOT / ".env")

BRAND_PRODUCTS = {
    "Conceit": [
        (5456, "Ribbed Tee — Heather Gray", "Tees"),
        (5457, "Ribbed Tee — Black", "Tees"),
        (5458, "Ribbed Long Sleeve — Heather Gray", "Long Sleeves"),
        (5459, "Cropped Basics Tee — Charcoal", "Tees"),
        (5460, "Conceit Logo Tee — Black", "Tees"),
        (5461, "Ribbed Long Sleeve — Sand", "Long Sleeves"),
        (5462, "Half-Zip Knit — Ivory", "Sweatshirts"),
        (5463, "Everyday Baggy Pants — Black", "Bottoms"),
    ],
    "Degraded": [
        (5465, "Camo Football Jersey", "Jerseys"),
        (5466, "Graphic Long Sleeve — Black", "Long Sleeves"),
        (5468, "Graphic Sleeveless Tee — Black", "Tees"),
        (5469, "Panel Jersey — Blue and Cream", "Jerseys"),
        (5470, "Graphic Tee — White", "Tees"),
        (5471, "Camouflage Cargo Shorts", "Bottoms"),
        (5472, "Graphic Cargo Pants — Black", "Bottoms"),
        (5473, "Track Pants — Green", "Bottoms"),
    ],
    "Seraphim": [
        (5483, "Surf Club Tee — Blue", "Tees"),
        (5484, "McQueen Tee — Red", "Tees"),
        (5485, "Rick and Morty Tee — Cream", "Tees"),
        (5486, "Logo Sweatshorts — Blue", "Bottoms"),
        (5487, "Airbrush Tee — Cream", "Tees"),
        (5488, "JB Graphic Tee — Cream", "Tees"),
        (5489, "Sid Skull Tee — Black", "Tees"),
        (5490, "Scooby Graphic Tee — Black", "Tees"),
    ],
}

app = Flask(__name__, static_folder=str(STATIC), static_url_path="")
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or secrets.token_urlsafe(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
)

ORDER_STATUSES = ("pending", "processing", "fulfilled")


def database_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        database=os.environ.get("MYSQL_DATABASE", "threadvault"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
    )


def fetch_one_dict(cursor) -> dict[str, Any] | None:
    """Narrow a dictionary cursor result at the MariaDB driver's dynamic boundary."""
    return cast(dict[str, Any] | None, cursor.fetchone())


def fetch_all_dicts(cursor) -> list[dict[str, Any]]:
    """Narrow dictionary cursor rows at the MariaDB driver's dynamic boundary."""
    return cast(list[dict[str, Any]], cursor.fetchall())


def api_error(message, status):
    return jsonify({"error": message}), status


def require_role(role):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if session.get("role") != role:
                return api_error("Please sign in with the required account type.", 401)
            return function(*args, **kwargs)
        return wrapped
    return decorate


def request_data():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def clean_text(value, field, maximum, required=True):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required.")
    if len(value) > maximum:
        raise ValueError(f"{field} must be at most {maximum} characters.")
    return value


def validate_product(data):
    name = clean_text(data.get("name"), "Product name", 160)
    category = clean_text(data.get("category"), "Category", 80)
    description = clean_text(data.get("description", ""), "Description", 3000, False)
    image_url = clean_text(data.get("image_url", ""), "Image URL", 500, False)
    try:
        price = Decimal(str(data.get("price")))
    except (InvalidOperation, TypeError):
        raise ValueError("Price must be a valid number.")
    if not price.is_finite() or price < 0 or price > Decimal("99999999.99"):
        raise ValueError("Price must be between 0 and 99,999,999.99.")

    size_rows = data.get("stock")
    if not isinstance(size_rows, list) or not size_rows:
        raise ValueError("Add at least one size and its stock quantity.")
    stock = []
    seen_sizes = set()
    for row in size_rows:
        if not isinstance(row, dict):
            raise ValueError("Each size entry must contain a size and quantity.")
        size = clean_text(row.get("size"), "Size", 40)
        quantity = row.get("quantity")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            raise ValueError(f"Stock for {size} must be a non-negative whole number.")
        if size.casefold() in seen_sizes:
            raise ValueError(f"Size {size} was entered more than once.")
        seen_sizes.add(size.casefold())
        stock.append((size, quantity))
    return name, category, description, price, image_url, stock


def product_rows(connection, seller_id=None):
    cursor = connection.cursor(dictionary=True)
    if seller_id is None:
        cursor.execute(
            "SELECT p.id, p.seller_id, p.name, p.category, p.description, "
            "p.price, p.image_url, u.shop_name "
            "FROM products p JOIN users u ON u.id = p.seller_id "
            "WHERE p.active = TRUE"
        )
    else:
        cursor.execute(
            "SELECT p.id, p.seller_id, p.name, p.category, p.description, "
            "p.price, p.image_url, u.shop_name "
            "FROM products p JOIN users u ON u.id = p.seller_id "
            "WHERE p.seller_id = %s AND p.active = TRUE",
            (seller_id,),
        )
    products = fetch_all_dicts(cursor)
    cursor.close()
    for product in products:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT size, quantity FROM product_stock WHERE product_id = %s",
            (product["id"],),
        )
        product["stock"] = fetch_all_dicts(cursor)
        cursor.close()
        product["price"] = float(product["price"])
    return products


def legacy_products():
    catalog_path = ROOT / "products.json"
    products = json.loads(catalog_path.read_text(encoding="utf-8-sig")) if catalog_path.exists() else []
    for product in products:
        product["id"] = f'legacy-{product["id"]}'
        product["shop_name"] = product.get("brand", "Archives")
        product["stock"] = []
    next_id = 109
    for shop_name, entries in BRAND_PRODUCTS.items():
        for image_number, name, category in entries:
            image_name = f"IMG_{image_number}.PNG"
            if not (ASSETS / image_name).is_file():
                continue
            products.append({
                "id": f"legacy-{next_id}",
                "brand": shop_name,
                "shop_name": shop_name,
                "name": name,
                "category": category,
                "description": f"{name}, from the {shop_name} collection.",
                "price": None,
                "image": f"/assets/{image_name}",
                "sizes": [],
                "stock": [],
            })
            next_id += 1
    return products


@app.after_request
def disable_page_caching(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(MySQLError)
def database_error(error):
    app.logger.error("MariaDB request failed: %s", error)
    return api_error(
        "The database is unavailable or not initialized. Start XAMPP MariaDB and import schema.sql.",
        503,
    )


@app.get("/")
def storefront():
    return send_from_directory(STATIC, "index.html")


@app.get("/seller")
def seller_page():
    return send_from_directory(STATIC, "seller.html")


@app.get("/account")
def customer_page():
    return send_from_directory(STATIC, "account.html")


@app.get("/assets/<path:filename>")
def product_asset(filename):
    return send_from_directory(ASSETS, filename)


@app.get("/api/health")
def health():
    connection = database_connection()
    connection.close()
    return jsonify({"status": "ok", "database": "connected"})


@app.get("/api/auth/me")
def current_account():
    if "user_id" not in session:
        return jsonify({"user": None})
    return jsonify({"user": {
        "id": session["user_id"],
        "email": session["email"],
        "role": session["role"],
        "display_name": session["display_name"],
        "shop_name": session.get("shop_name"),
    }})


@app.post("/api/auth/register")
def register():
    data = request_data()
    try:
        email = clean_text(data.get("email"), "Email", 254).lower()
        password = data.get("password")
        if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
            return api_error("Password must contain 8 to 128 characters.", 400)
        role = data.get("role")
        if role not in ("seller", "customer"):
            return api_error("Account type must be seller or customer.", 400)
        display_name = clean_text(data.get("display_name"), "Name", 120)
        shop_name = None
        if role == "seller":
            shop_name = clean_text(data.get("shop_name"), "Shop name", 120)
    except ValueError as error:
        return api_error(str(error), 400)

    connection = database_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, role, display_name, shop_name) "
            "VALUES (%s, %s, %s, %s, %s)",
            (email, generate_password_hash(password), role, display_name, shop_name),
        )
        connection.commit()
        user_id = cursor.lastrowid
    except MySQLError as error:
        connection.rollback()
        if error.errno == 1062:
            return api_error("An account with that email already exists.", 409)
        raise
    finally:
        cursor.close()
        connection.close()

    session.clear()
    session.permanent = True
    session.update(
        user_id=user_id,
        email=email,
        role=role,
        display_name=display_name,
        shop_name=shop_name,
    )
    return jsonify({"user": {
        "id": user_id,
        "email": email,
        "role": role,
        "display_name": display_name,
        "shop_name": shop_name,
    }}), 201


@app.post("/api/auth/login")
def login():
    data = request_data()
    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return api_error("Email and password are required.", 400)
    connection = database_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
    user = fetch_one_dict(cursor)
    cursor.close()
    connection.close()
    if user is None or not check_password_hash(user["password_hash"], password):
        return api_error("Email or password is incorrect.", 401)

    session.clear()
    session.permanent = True
    session.update(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        display_name=user["display_name"],
        shop_name=user["shop_name"],
    )
    return current_account()


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/products")
def list_products():
    connection = database_connection()
    products = product_rows(connection)
    connection.close()
    products = [{
        **product,
        "brand": product["shop_name"],
        "image": product["image_url"] or "",
        "sizes": [row["size"] for row in product["stock"] if row["quantity"] > 0],
    } for product in products]
    products.extend(legacy_products())
    products = sort_catalog(search_catalog(products, request.args.get("q", "")))
    return jsonify([{
        "id": product["id"],
        "brand": product["brand"],
        "seller_id": product.get("seller_id"),
        "name": product["name"],
        "category": product["category"],
        "description": product["description"],
        "price": float(product["price"]) if product["price"] is not None else None,
        "image": product["image"],
        "sizes": product["sizes"],
        "stock": {row["size"]: row["quantity"] for row in product["stock"]},
    } for product in products])


@app.get("/api/seller/products")
@require_role("seller")
def seller_products():
    connection = database_connection()
    products = product_rows(connection, session["user_id"])
    connection.close()
    return jsonify(products)


@app.post("/api/seller/products")
@require_role("seller")
def create_product():
    try:
        name, category, description, price, image_url, stock = validate_product(request_data())
    except ValueError as error:
        return api_error(str(error), 400)
    connection = database_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO products "
            "(seller_id, name, category, description, price, image_url) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (session["user_id"], name, category, description, price, image_url or None),
        )
        product_id = cursor.lastrowid
        cursor.executemany(
            "INSERT INTO product_stock (product_id, size, quantity) VALUES (%s, %s, %s)",
            [(product_id, size, quantity) for size, quantity in stock],
        )
        connection.commit()
    except MySQLError:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    return jsonify({"id": product_id}), 201


@app.put("/api/seller/products/<int:product_id>")
@require_role("seller")
def update_product(product_id):
    try:
        name, category, description, price, image_url, stock = validate_product(request_data())
    except ValueError as error:
        return api_error(str(error), 400)
    connection = database_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM products WHERE id = %s AND seller_id = %s AND active = TRUE FOR UPDATE",
        (product_id, session["user_id"]),
    )
    if fetch_one_dict(cursor) is None:
        cursor.close()
        connection.close()
        return api_error("Product not found in your shop.", 404)
    try:
        cursor.execute(
            "UPDATE products SET name = %s, category = %s, description = %s, "
            "price = %s, image_url = %s WHERE id = %s AND seller_id = %s",
            (name, category, description, price, image_url or None, product_id, session["user_id"]),
        )
        cursor.execute("DELETE FROM product_stock WHERE product_id = %s", (product_id,))
        cursor.executemany(
            "INSERT INTO product_stock (product_id, size, quantity) VALUES (%s, %s, %s)",
            [(product_id, size, quantity) for size, quantity in stock],
        )
        connection.commit()
    except MySQLError:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    return jsonify({"ok": True})


@app.delete("/api/seller/products/<int:product_id>")
@require_role("seller")
def delete_product(product_id):
    connection = database_connection()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE products SET active = FALSE WHERE id = %s AND seller_id = %s AND active = TRUE",
        (product_id, session["user_id"]),
    )
    changed = cursor.rowcount
    connection.commit()
    cursor.close()
    connection.close()
    if not changed:
        return api_error("Product not found in your shop.", 404)
    return jsonify({"ok": True})


@app.post("/api/seller/upload")
@require_role("seller")
def upload_product_image():
    uploaded = request.files.get("image")
    if uploaded is None or not uploaded.filename:
        return api_error("Choose an image file to upload.", 400)
    filename = secure_filename(uploaded.filename)
    extension = Path(filename).suffix.lower()
    allowed_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    if extension not in allowed_types or uploaded.mimetype != allowed_types[extension]:
        return api_error("Use a PNG, JPG, JPEG, or WEBP image.", 400)
    upload_folder = STATIC / "uploads"
    upload_folder.mkdir(exist_ok=True)
    saved_name = f"{uuid4().hex}{extension}"
    uploaded.save(upload_folder / saved_name)
    return jsonify({"image_url": f"/uploads/{saved_name}"}), 201


@app.post("/api/orders")
@require_role("customer")
def place_order():
    data = request_data()
    items = data.get("items")
    priority = data.get("priority", "standard")
    if not isinstance(items, list) or not items:
        return api_error("Your bag is empty.", 400)
    if priority not in PRIORITY_RANK:
        return api_error("Choose urgent, express, or standard fulfillment priority.", 400)
    validated_lines: list[CheckoutLine] = []
    for item in items:
        if not isinstance(item, dict):
            return api_error("Each bag entry must be a product, size, and quantity.", 400)
        product_id, size, quantity = item.get("product_id"), item.get("size"), item.get("quantity")
        if not isinstance(product_id, int) or isinstance(product_id, bool):
            return api_error("Product id must be an integer.", 400)
        if not isinstance(size, str) or not size.strip():
            return api_error("A size is required for each item.", 400)
        if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 10:
            return api_error("Quantity must be between 1 and 10.", 400)
        validated_lines.append((product_id, size.strip(), quantity))
    ordered_lines = order_lines_in_sequence(validated_lines)

    connection = database_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO orders (customer_id, priority) VALUES (%s, %s)",
            (session["user_id"], priority),
        )
        order_id = cursor.lastrowid
        for product_id, size, quantity in ordered_lines:
            cursor.execute(
                "SELECT p.seller_id, p.price, p.active, s.quantity "
                "FROM products p JOIN product_stock s ON s.product_id = p.id "
                "WHERE p.id = %s AND s.size = %s FOR UPDATE",
                (product_id, size),
            )
            product = fetch_one_dict(cursor)
            if not product or not product["active"]:
                raise ValueError("A product or size in your bag is no longer available.")
            if product["quantity"] < quantity:
                raise ValueError(f"Not enough stock remains for product {product_id}, size {size}.")
            cursor.execute(
                "UPDATE product_stock SET quantity = quantity - %s "
                "WHERE product_id = %s AND size = %s",
                (quantity, product_id, size),
            )
            cursor.execute(
                "INSERT INTO order_items "
                "(order_id, product_id, seller_id, size, quantity, unit_price) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (order_id, product_id, product["seller_id"], size, quantity, product["price"]),
            )
        connection.commit()
    except ValueError as error:
        connection.rollback()
        return api_error(str(error), 409)
    except MySQLError:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    return jsonify({"order_id": order_id, "status": "pending", "priority": priority}), 201


@app.get("/api/orders")
@require_role("customer")
def customer_orders():
    connection = database_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT o.id AS order_id, o.priority, o.created_at, "
        "oi.id AS item_id, oi.product_id, oi.size, oi.quantity, oi.unit_price, oi.status, "
        "p.name, u.shop_name "
        "FROM orders o JOIN order_items oi ON oi.order_id = o.id "
        "JOIN products p ON p.id = oi.product_id "
        "JOIN users u ON u.id = oi.seller_id "
        "WHERE o.customer_id = %s ORDER BY o.id DESC, oi.id",
        (session["user_id"],),
    )
    rows = fetch_all_dicts(cursor)
    cursor.close()
    connection.close()
    return jsonify([{
        **row,
        "unit_price": float(row["unit_price"]),
        "created_at": row["created_at"].isoformat(),
    } for row in rows])


@app.get("/api/seller/orders")
@require_role("seller")
def seller_orders():
    connection = database_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT oi.id AS item_id, oi.order_id, oi.product_id, oi.size, oi.quantity, "
        "oi.unit_price, oi.status, o.priority, o.created_at, p.name, "
        "customer.display_name AS customer_name "
        "FROM order_items oi JOIN orders o ON o.id = oi.order_id "
        "JOIN products p ON p.id = oi.product_id "
        "JOIN users customer ON customer.id = o.customer_id "
        "WHERE oi.seller_id = %s",
        (session["user_id"],),
    )
    rows = fetch_all_dicts(cursor)
    cursor.close()
    connection.close()

    ordered = order_work_list(rows)
    for row in ordered:
        row["unit_price"] = float(row["unit_price"])
        row["created_at"] = row["created_at"].isoformat()
    return jsonify(ordered)


@app.patch("/api/seller/order-items/<int:item_id>")
@require_role("seller")
def update_order_item(item_id):
    data = request_data()
    new_status = data.get("status")
    if new_status not in ORDER_STATUSES[1:]:
        return api_error("Status must be processing or fulfilled.", 400)
    connection = database_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT status FROM order_items WHERE id = %s AND seller_id = %s FOR UPDATE",
        (item_id, session["user_id"]),
    )
    row = fetch_one_dict(cursor)
    if row is None:
        cursor.close()
        connection.close()
        return api_error("Order item not found in your shop.", 404)
    old_status = row["status"]
    if ORDER_STATUSES.index(new_status) != ORDER_STATUSES.index(old_status) + 1:
        cursor.close()
        connection.close()
        return api_error(f"Status must move one step forward from {old_status}.", 409)
    cursor.execute(
        "UPDATE order_items SET status = %s WHERE id = %s AND seller_id = %s AND status = %s",
        (new_status, item_id, session["user_id"], old_status),
    )
    cursor.execute(
        "INSERT INTO order_status_history "
        "(order_item_id, seller_id, old_status, new_status) VALUES (%s, %s, %s, %s)",
        (item_id, session["user_id"], old_status, new_status),
    )
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"ok": True, "status": new_status})


@app.post("/api/seller/orders/undo-last-status")
@require_role("seller")
def undo_last_status():
    connection = database_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, order_item_id, old_status, new_status FROM order_status_history "
        "WHERE seller_id = %s AND undone_at IS NULL ORDER BY id",
        (session["user_id"],),
    )
    history = fetch_all_dicts(cursor)
    event = latest_undoable(history)
    if event is None:
        cursor.close()
        connection.close()
        return api_error("There is no status change to undo.", 409)
    cursor.execute(
        "SELECT status FROM order_items WHERE id = %s AND seller_id = %s FOR UPDATE",
        (event["order_item_id"], session["user_id"]),
    )
    item = fetch_one_dict(cursor)
    if not item or item["status"] != event["new_status"]:
        connection.rollback()
        cursor.close()
        connection.close()
        return api_error("That status can no longer be undone because it has changed.", 409)
    cursor.execute(
        "UPDATE order_items SET status = %s WHERE id = %s",
        (event["old_status"], event["order_item_id"]),
    )
    cursor.execute(
        "UPDATE order_status_history SET undone_at = CURRENT_TIMESTAMP WHERE id = %s",
        (event["id"],),
    )
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"ok": True, "restored_status": event["old_status"]})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
