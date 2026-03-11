from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="pharmacy_db"
)

cursor = db.cursor(dictionary=True)

# SIGNUP
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error":"All fields are required"}),400

    # Check if username exists
    cursor.execute("SELECT * FROM users WHERE username=%s",(username,))
    if cursor.fetchone():
        return jsonify({"error":"Username already exists"}),400

    hashed_password = generate_password_hash(password)
    cursor.execute("INSERT INTO users (username,password) VALUES (%s,%s)", (username, hashed_password))
    db.commit()

    return jsonify({"message":"User created successfully"})


# LOGIN
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error":"All fields are required"}),400

    cursor.execute("SELECT * FROM users WHERE username=%s",(username,))
    user = cursor.fetchone()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error":"Invalid username or password"}),401

    return jsonify({"message":"Login successful"})
# ------------------------
# MEDICINES
# ------------------------

@app.route("/medicines", methods=["GET"])
def get_medicines():
    cursor.execute("SELECT * FROM medicines")
    return jsonify(cursor.fetchall())


@app.route("/add_medicine", methods=["POST"])
def add_medicine():

    data = request.json

    query = """
    INSERT INTO medicines (name,batch,mfg,expiry,quantity,price,prescription)
    VALUES (%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        data["name"],
        data["batch"],
        data["mfg"],
        data["expiry"],
        int(data["quantity"]),
        float(data["price"]),
        data["prescription"]
    )

    cursor.execute(query,values)
    db.commit()

    return jsonify({"message":"Medicine added"})


@app.route("/delete_medicine/<batch>", methods=["DELETE"])
def delete_medicine(batch):

    cursor.execute("DELETE FROM medicines WHERE batch=%s",(batch,))
    db.commit()

    return jsonify({"message":"Medicine deleted"})


@app.route("/edit_medicine/<batch>", methods=["PUT"])
def edit_medicine(batch):

    data = request.json

    query = """
    UPDATE medicines
    SET quantity=%s,price=%s,expiry=%s
    WHERE batch=%s
    """

    values = (
        int(data["quantity"]),
        float(data["price"]),
        data["expiry"],
        batch
    )

    cursor.execute(query,values)
    db.commit()

    return jsonify({"message":"Medicine updated"})


# ------------------------
# PURCHASE
# ------------------------

@app.route("/purchase", methods=["POST"])
def purchase():

    data = request.json
    items = data["items"]

    for item in items:

        cursor.execute(
            "SELECT * FROM medicines WHERE name=%s AND batch=%s",
            (item["name"],item["batch"])
        )

        med = cursor.fetchone()

        if med:

            new_qty = med["quantity"] + int(item["quantity"])

            cursor.execute(
                "UPDATE medicines SET quantity=%s WHERE id=%s",
                (new_qty,med["id"])
            )

        else:

            cursor.execute(
            """
            INSERT INTO medicines
            (name,batch,mfg,expiry,quantity,price,prescription)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                item["name"],
                item["batch"],
                item["mfg"],
                item["expiry"],
                int(item["quantity"]),
                float(item["costPrice"]),
                "No"
            )
            )

    db.commit()

    return jsonify({"message":"Purchase successful"})


# ------------------------
# BILLING
# ------------------------

@app.route("/sell", methods=["POST"])
def sell():

    data = request.json

    items = data["items"]
    prescription_id = data.get("prescription_id")

    total_amount = 0

    cursor.execute(
        "INSERT INTO sales (sale_date,total_amount) VALUES (%s,%s)",
        (datetime.today().strftime("%Y-%m-%d"),0)
    )

    sale_id = cursor.lastrowid


    for item in items:

        cursor.execute(
            "SELECT * FROM medicines WHERE name=%s AND batch=%s",
            (item["name"],item["batch"])
        )

        med = cursor.fetchone()

        if not med:
            return jsonify({"error":"Medicine not found"}),400


        if med["prescription"] == "Yes" and not prescription_id:
            return jsonify({"error":f"{med['name']} requires prescription"}),400


        qty = int(item["quantity"])

        if med["quantity"] < qty:
            return jsonify({"error":"Not enough stock"}),400


        new_qty = med["quantity"] - qty


        cursor.execute(
            "UPDATE medicines SET quantity=%s WHERE id=%s",
            (new_qty,med["id"])
        )


        amount = med["price"] * qty

        total_amount += amount


        cursor.execute(
        """
        INSERT INTO sale_items
        (sale_id,medicine_name,batch,quantity,price,amount)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            sale_id,
            item["name"],
            item["batch"],
            qty,
            med["price"],
            amount
        )
        )


    cursor.execute(
        "UPDATE sales SET total_amount=%s WHERE id=%s",
        (total_amount,sale_id)
    )

    db.commit()

    return jsonify({
        "message":"Sale completed",
        "total":total_amount
    })





# ------------------------
# STOCK
# ------------------------

@app.route("/low_stock")
def low_stock():

    cursor.execute("SELECT * FROM medicines WHERE quantity < 10")

    return jsonify(cursor.fetchall())


@app.route("/expired_medicines")
def expired():

    cursor.execute("SELECT * FROM medicines WHERE expiry < CURDATE()")

    return jsonify(cursor.fetchall())
@app.route("/sales_report", methods=["GET"])
def sales_report():

    # TOTAL SALES
    cursor.execute("SELECT IFNULL(SUM(total_amount),0) AS total FROM sales")
    total_revenue = cursor.fetchone()["total"]

    # DAILY SALES
    cursor.execute("""
    SELECT IFNULL(SUM(total_amount),0) AS daily
    FROM sales
    WHERE DATE(sale_date) = CURDATE()
    """)
    daily_sales = cursor.fetchone()["daily"]

    # MONTHLY SALES
    cursor.execute("""
    SELECT IFNULL(SUM(total_amount),0) AS monthly
    FROM sales
    WHERE MONTH(sale_date) = MONTH(CURDATE())
    AND YEAR(sale_date) = YEAR(CURDATE())
    """)
    monthly_sales = cursor.fetchone()["monthly"]

   # ALL SALES
    cursor.execute("""
    SELECT id, DATE_FORMAT(sale_date,'%d-%m-%Y') AS sale_date, total_amount
    FROM sales
    ORDER BY id DESC
    """)



    all_sales = cursor.fetchall()

    return jsonify({
        "daily_sales": daily_sales,
        "monthly_sales": monthly_sales,
        "total_revenue": total_revenue,
        "all_sales": all_sales
    })
@app.route("/sale_items/<int:sale_id>", methods=["GET"])
def sale_items(sale_id):

    cursor.execute("""
    SELECT medicine_name,batch,quantity,price,amount
    FROM sale_items
    WHERE sale_id=%s
    """,(sale_id,))

    rows = cursor.fetchall()

    items = []

    for r in rows:

        items.append({
            "medicine_name": r["medicine_name"],
            "batch": r["batch"],
            "quantity": r["quantity"],
            "price": r["price"],
            "amount": r["amount"]
        })

    return jsonify(items)
@app.route("/expiring_medicines")
def expiring():

    cursor.execute(
    """
    SELECT * FROM medicines
    WHERE expiry BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
    """
    )

    return jsonify(cursor.fetchall())


# ------------------------

if __name__ == "__main__":
    app.run(debug=True)