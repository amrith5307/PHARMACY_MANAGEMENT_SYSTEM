from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="pharmacy_db"
    )

# ------------------------
# SIGNUP
# ------------------------
@app.route("/signup", methods=["POST"])
def signup():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    data = request.json
    username = data.get("username")
    password = data.get("password")

    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    if cursor.fetchone():
        return jsonify({"error": "Username exists"}), 400

    hashed = generate_password_hash(password)

    cursor.execute(
        "INSERT INTO users (username,password) VALUES (%s,%s)",
        (username, hashed)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "User created"})


# ------------------------
# LOGIN
# ------------------------
@app.route("/login", methods=["POST"])
def login():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    data = request.json

    cursor.execute("SELECT * FROM users WHERE username=%s", (data["username"],))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user or not check_password_hash(user["password"], data["password"]):
        return jsonify({"error": "Invalid"}), 401

    return jsonify({"message": "Login success"})


# ------------------------
# MEDICINES
# ------------------------
@app.route("/medicines")
def medicines():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM medicines")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


# ------------------------
# ADD MEDICINE
# ------------------------
@app.route("/add_medicine", methods=["POST"])
def add_medicine():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    data = request.json

    cursor.execute("""
        INSERT INTO medicines (name,batch,mfg,expiry,quantity,price,prescription)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["name"],
        data["batch"],
        data["mfg"],
        data["expiry"],
        int(data["quantity"]),
        float(data["price"]),
        data["prescription"]
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Medicine added"})


# ------------------------
# DELETE MEDICINE
# ------------------------
@app.route("/delete_medicine/<batch>", methods=["DELETE"])
def delete_medicine(batch):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("DELETE FROM medicines WHERE batch=%s", (batch,))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Deleted"})


# ------------------------
# EDIT MEDICINE
# ------------------------
@app.route("/edit_medicine/<batch>", methods=["PUT"])
def edit_medicine(batch):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    data = request.json

    cursor.execute("""
        UPDATE medicines
        SET quantity=%s, price=%s, expiry=%s
        WHERE batch=%s
    """, (
        int(data["quantity"]),
        float(data["price"]),
        data["expiry"],
        batch
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Updated"})


# ------------------------
# PURCHASE
# ------------------------
@app.route("/purchase", methods=["POST"])
def purchase():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    data = request.json
    items = data["items"]

    for item in items:

        cursor.execute(
            "SELECT * FROM medicines WHERE name=%s AND batch=%s",
            (item["name"], item["batch"])
        )

        med = cursor.fetchone()

        if med:
            cursor.execute(
                "UPDATE medicines SET quantity=%s WHERE id=%s",
                (med["quantity"] + int(item["quantity"]), med["id"])
            )
            medicine_id = med["id"]
        else:
            cursor.execute("""
                INSERT INTO medicines
                (name,batch,mfg,expiry,quantity,price,prescription)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                item["name"],
                item["batch"],
                item["mfg"],
                item["expiry"],
                int(item["quantity"]),
                float(item["costPrice"]),
                "No"
            ))
            medicine_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO purchases
            (medicine_id, cost_price, quantity, purchase_date)
            VALUES (%s,%s,%s,CURDATE())
        """, (
            medicine_id,
            float(item["costPrice"]),
            int(item["quantity"])
        ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Purchase successful"})


# ------------------------
# SELL
# ------------------------
@app.route("/sell", methods=["POST"])
def sell():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    data = request.json
    items = data["items"]

    cursor.execute(
        "INSERT INTO sales (sale_date,total_amount) VALUES (%s,%s)",
        (datetime.today().strftime("%Y-%m-%d"), 0)
    )

    sale_id = cursor.lastrowid
    total = 0

    for item in items:

        cursor.execute(
            "SELECT * FROM medicines WHERE name=%s AND batch=%s",
            (item["name"], item["batch"])
        )

        med = cursor.fetchone()

        qty = int(item["quantity"])
        price = float(item["price"])

        cursor.execute(
            "UPDATE medicines SET quantity=%s WHERE id=%s",
            (med["quantity"] - qty, med["id"])
        )

        amount = price * qty
        total += amount

        cursor.execute("""
            INSERT INTO sale_items
            (sale_id,medicine_name,batch,quantity,price,amount)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            sale_id,
            item["name"],
            item["batch"],
            qty,
            price,
            amount
        ))

    cursor.execute(
        "UPDATE sales SET total_amount=%s WHERE id=%s",
        (total, sale_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Sold", "total": total})


# ------------------------
# SALE ITEMS
# ------------------------
@app.route("/sale_items/<int:id>")
def sale_items(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM sale_items WHERE sale_id=%s", (id,))
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


# ------------------------
# SALES REPORT
# ------------------------
@app.route("/sales_report")
def sales_report():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT IFNULL(SUM(total_amount),0) total FROM sales")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT IFNULL(SUM(total_amount),0) daily FROM sales WHERE DATE(sale_date)=CURDATE()")
    daily = cursor.fetchone()["daily"]

    cursor.execute("SELECT IFNULL(SUM(total_amount),0) monthly FROM sales WHERE MONTH(sale_date)=MONTH(CURDATE())")
    monthly = cursor.fetchone()["monthly"]

    cursor.execute("""
        SELECT id, DATE_FORMAT(sale_date,'%d-%m-%Y') sale_date, total_amount 
        FROM sales
        ORDER BY id DESC
    """)
    all_sales = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "daily_sales": daily,
        "monthly_sales": monthly,
        "total_revenue": total,
        "all_sales": all_sales
    })


# ------------------------
# STOCK ALERT
# ------------------------
@app.route("/low_stock")
def low_stock():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM medicines WHERE quantity < 10")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


@app.route("/expired_medicines")
def expired_medicines():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM medicines WHERE expiry < CURDATE()")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


@app.route("/expiring_medicines")
def expiring_medicines():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM medicines
        WHERE expiry BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
    """)
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


# ------------------------
# BEST MEDICINE REPORT
# ------------------------
@app.route("/best_medicine")
def best_medicine():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
        m.name AS medicine,

        s.total_sold,
        s.total_revenue,

        (s.total_revenue / s.total_sold) AS selling_price,

        p.total_purchase_cost,
        p.total_purchased_qty,

        (p.total_purchase_cost / p.total_purchased_qty) AS cost_price,

        (s.total_revenue - (p.total_purchase_cost / p.total_purchased_qty) * s.total_sold) AS profit

    FROM medicines m

    JOIN (
        SELECT medicine_name,
               SUM(quantity) AS total_sold,
               SUM(amount) AS total_revenue
        FROM sale_items
        GROUP BY medicine_name
    ) s ON s.medicine_name = m.name

    JOIN (
        SELECT medicine_id,
               SUM(quantity) AS total_purchased_qty,
               SUM(cost_price * quantity) AS total_purchase_cost
        FROM purchases
        GROUP BY medicine_id
    ) p ON p.medicine_id = m.id
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


# ------------------------
if __name__ == "__main__":
    app.run(debug=True)