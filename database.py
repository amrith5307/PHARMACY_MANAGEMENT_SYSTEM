import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="pharmacy_db"
    )
    return conn