from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ------------------------
# In-memory storage
# ------------------------
medicines = []
sales = []

# ------------------------
# Inventory Routes
# ------------------------

@app.route("/medicines", methods=["GET"])
def get_medicines():
    return jsonify(medicines)

@app.route("/add_medicine", methods=["POST"])
def add_medicine():
    data = request.json
    medicines.append({
        "name": data["name"],
        "batch": data["batch"],
        "mfg": data["mfg"],
        "expiry": data["expiry"],
        "quantity": int(data["quantity"]),
        "price": float(data["price"]),
        "prescription": data["prescription"]
    })
    return jsonify({"message": "Medicine added successfully"})

@app.route("/delete_medicine/<batch>", methods=["DELETE"])
def delete_medicine(batch):
    global medicines
    medicines = [m for m in medicines if m["batch"] != batch]
    return jsonify({"message":"Medicine deleted"})

@app.route("/edit_medicine/<batch>", methods=["PUT"])
def edit_medicine(batch):
    data = request.json
    for m in medicines:
        if m["batch"] == batch:
            m["quantity"] = int(data.get("quantity", m["quantity"]))
            m["price"] = float(data.get("price", m["price"]))
            m["expiry"] = data.get("expiry", m["expiry"])
            break
    return jsonify({"message":"Medicine updated"})

# ------------------------
# Purchase Module
# ------------------------

@app.route("/purchase", methods=["POST"])
def purchase_medicines():
    data = request.json
    items = data["items"]  # list of purchase items

    for item in items:
        # check if same medicine + batch exists
        exists = False
        for m in medicines:
            if m["name"] == item["name"] and m["batch"] == item["batch"]:
                m["quantity"] += int(item["quantity"])
                exists = True
                break
        if not exists:
            medicines.append({
                "name": item["name"],
                "batch": item["batch"],
                "mfg": item["mfg"],
                "expiry": item["expiry"],
                "quantity": int(item["quantity"]),
                "price": float(item["costPrice"]),
                "prescription": "No"
            })
    return jsonify({"message":"Purchase processed"})

# ------------------------
# Billing Module
# ------------------------

@app.route("/sell", methods=["POST"])
def sell_medicines():
    data = request.json
    items = data["items"]
    total_amount = 0
    sale_record = {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "items": [],
        "total": 0
    }

    for item in items:
        for m in medicines:
            if m["name"] == item["name"] and m["batch"] == item["batch"]:
                if int(m["quantity"]) >= int(item["quantity"]):
                    m["quantity"] -= int(item["quantity"])
                    amount = float(m["price"]) * int(item["quantity"])
                    total_amount += amount
                    sale_record["items"].append({
                        "name": m["name"],
                        "batch": m["batch"],
                        "quantity": item["quantity"],
                        "price": m["price"],
                        "amount": amount
                    })
                else:
                    return jsonify({"error": f"Not enough stock for {m['name']} batch {m['batch']}"}), 400

    sale_record["total"] = total_amount
    sales.append(sale_record)
    return jsonify({"message": "Sale completed", "total": total_amount, "sale": sale_record})

# ------------------------
# Sales Report
# ------------------------

@app.route("/sales_report", methods=["GET"])
def sales_report():
    today = datetime.today().strftime("%Y-%m-%d")
    daily_sales = sum(s["total"] for s in sales if s["date"] == today)
    monthly_sales = sum(s["total"] for s in sales if s["date"][:7] == today[:7])
    total_revenue = sum(s["total"] for s in sales)
    return jsonify({
        "daily_sales": daily_sales,
        "monthly_sales": monthly_sales,
        "total_revenue": total_revenue,
        "all_sales": sales
    })

# ------------------------
# Stock & Expiry
# ------------------------

@app.route("/low_stock", methods=["GET"])
def low_stock():
    low = [m for m in medicines if int(m["quantity"]) < 10]
    return jsonify(low)

@app.route("/expired_medicines", methods=["GET"])
def expired_medicines():
    today = datetime.today().date()
    expired = [m for m in medicines if datetime.strptime(m["expiry"], "%Y-%m-%d").date() < today]
    return jsonify(expired)

@app.route("/expiring_medicines", methods=["GET"])
def expiring_medicines():
    today = datetime.today().date()
    soon = today + timedelta(days=30)
    expiring = [m for m in medicines 
                if today <= datetime.strptime(m["expiry"], "%Y-%m-%d").date() <= soon]
    return jsonify(expiring)

# ------------------------
if __name__ == "__main__":
    app.run(debug=True)