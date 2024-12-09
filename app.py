import sqlite3
import base64
from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Function to create the admin login database and table if not present
def create_admin_login_db():
    conn = sqlite3.connect('admin_login.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_login (
            UserName TEXT NOT NULL CHECK (LENGTH(UserName) BETWEEN 5 AND 25),
            Password TEXT NOT NULL CHECK (LENGTH(Password) BETWEEN 6 AND 25)
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM admin_login')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO admin_login (UserName, Password) VALUES (?, ?)', ('Admin', 'Admin@123'))
    conn.commit()
    conn.close()

# Function to create the customer database and table if not present
def create_customer_db():
    conn = sqlite3.connect('customer.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL CHECK (LENGTH(name) BETWEEN 1 AND 100),
            passport_number TEXT NOT NULL UNIQUE,
            reference_number TEXT NOT NULL UNIQUE,
            contact_number TEXT NOT NULL CHECK (LENGTH(contact_number) BETWEEN 10 AND 15),
            job_designation TEXT NOT NULL,
            profile_picture BLOB
        )
    ''')
    conn.commit()
    conn.close()

# Add this function to create the AuthenticUser table
def create_authentic_user_db():
    conn = sqlite3.connect('customer.db')  # Reuse the same database
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS AuthenticUser (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            reference_number TEXT NOT NULL UNIQUE,
            passport_number TEXT NOT NULL UNIQUE,
            multiple_image_field TEXT  -- Comma-separated file paths for simplicity
        )
    ''')
    print("AuthenticUser table checked/created successfully.")
    conn.commit()
    conn.close()

@app.route('/debug/tables')
def debug_tables():
    conn = sqlite3.connect('customer.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return {'tables': tables}


# Function to convert binary data to base64 encoding
def image_to_base64(image_data):
    return base64.b64encode(image_data).decode('utf-8')

# Register the custom filter with Flask
app.jinja_env.filters['b64encode'] = image_to_base64

@app.route('/')
def index():
    return render_template('index.html')

#=========================================================
#=======================  Templats =======================
#=========================================================

@app.route('/eden_job_verification', methods=['GET', 'POST'])
def eden_job_verification():
    error = None
    user_images = []

    if request.method == 'POST':
        reference_number = request.form.get('reference_number')
        passport_number = request.form.get('passport_number')

        # Debugging: print input data
        print(f"Received POST data - Reference Number: {reference_number}, Passport Number: {passport_number}")

        # Connect to SQLite database
        conn = sqlite3.connect('customer.db')
        cursor = conn.cursor()

        # Query to fetch user data from AuthenticUser table
        # query = '''
        #     SELECT multiple_image_field FROM AuthenticUser
        #     WHERE reference_number = ? AND passport_number = ?
        # '''
        cursor.execute("SELECT multiple_image_field FROM AuthenticUser WHERE reference_number = ? AND passport_number = ?", (reference_number, passport_number))
        # print(f"Executing query: {query} with params ({reference_number}, {passport_number})")

        # cursor.execute(query, (reference_number, passport_number))
        result = cursor.fetchone()

        # Debugging: print query result
        print(f"Query result: {result}")

        conn.close()

        if result:
            # Process the image paths
            image_paths = [path.strip() for path in result[0].split(',')] if result[0] else []
            print(f"Image paths extracted: {image_paths}")

            for path in image_paths:
                try:
                    with open(path.strip(), "rb") as image_file:
                        # Convert image to base64
                        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                        user_images.append(encoded_image)
                        print(f"Successfully encoded image: {path}")
                except FileNotFoundError:
                    # Log missing files but proceed with valid ones
                    error = f"Missing image: {path}"
                    print(f"File not found: {path}")

            if user_images:
                # Debugging: print successfully encoded images
                print(f"Encoded images: {user_images}")
                # Redirect to a new template with valid images
                return render_template('user_images.html', images=user_images)
            else:
                error = "No valid images found for the provided credentials."
                print(error)
        else:
            error = "Your record does not exist. Please check your credentials."
            print(error)

    # Debugging: print final error if any
    if error:
        print(f"Final error message: {error}")

    return render_template('eden_job_verification.html', error=error)


UPLOAD_FOLDER = 'static/uploads/'  # Folder to store uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Check if a file is an allowed image type."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_authentic_user():
    error = None
    success = None

    if request.method == 'POST':
        name = request.form.get('name')
        reference_number = request.form.get('reference_number')
        passport_number = request.form.get('passport_number')
        images = request.files.getlist('images')  # Get multiple image files

        # Validate input
        if not name or not reference_number or not passport_number:
            error = "All fields are required."
        elif not images:
            error = "At least one image must be uploaded."
        else:
            # Save images to the upload folder
            saved_image_paths = []
            for image in images:
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(filepath)
                    saved_image_paths.append(filepath)
                else:
                    error = "Invalid file type. Only PNG, JPG, and JPEG are allowed."
                    break

            if not error:
                # Store user data in the database
                try:
                    conn = sqlite3.connect('customer.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO AuthenticUser (name, reference_number, passport_number, multiple_image_field)
                        VALUES (?, ?, ?, ?)
                    ''', (name, reference_number, passport_number, ','.join(saved_image_paths)))
                    conn.commit()
                    conn.close()
                    success = "User added successfully with images uploaded."
                except sqlite3.IntegrityError as e:
                    error = "User with this reference number or passport number already exists."

    return render_template('add_authentic_user.html', error=error, success=success)
# if __name__ == '__main__':
#     app.run(debug=True)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect('admin_login.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admin_login WHERE UserName = ? AND Password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid username or password."

    return render_template('admin.html', error=error)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/add_customer', methods=['POST'])
def add_customer():
    name = request.form['name']
    passport_number = request.form['passport_number']
    reference_number = request.form['reference_number']
    contact_number = request.form['contact_number']
    job_designation = request.form['job_designation']
    profile_picture = request.files['profile_picture'].read()  # Read profile picture as binary data

    conn = sqlite3.connect('customer.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO customer (name, passport_number, reference_number, contact_number, job_designation, profile_picture)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, passport_number, reference_number, contact_number, job_designation, profile_picture))
    conn.commit()
    conn.close()

    return render_template('dashboard.html', message="Customer added successfully!")

if __name__ == '__main__':
    create_admin_login_db()
    create_customer_db()
    create_authentic_user_db()
    app.run(debug=True)
