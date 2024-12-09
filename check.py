import sqlite3

try:
    # Try to connect to the database
    conn = sqlite3.connect('admin_login.db')
    conn.close()  # Close the connection immediately after chec  # Connection successful
    print("everthing is good")
except sqlite3.Error as e:
    print(f"Database connection error: {e}")

