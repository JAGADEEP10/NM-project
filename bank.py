from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for flash messages

# Database configuration
db_config = {
    'host': 'bank.crqmssgockvo.ap-south-1.rds.amazonaws.com',
    'user': 'admin',
    'password': 'Surya123456',
    'database': 'bank'
}

cnxpool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",
                                                      pool_size=5,
                                                      **db_config)

# Function to establish a database connection
def get_db_connection():
    try:
        return cnxpool.get_connection()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

@app.route("/test-db-connection")
def test_db_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")  # Test query to check connection
        db_name = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"Connected to the database: {db_name[0]}"
    except mysql.connector.Error as err:
        return f"Error: {err}"

@app.route("/")
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn:
            cursor.close()
            conn.close()
    return render_template("index.html")

@app.route("/register", methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']
        aadhar_number = request.form['aadhar_number']
        pan_card = request.form['pan_card']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            flash("Email already exists! Please log in.")
            return redirect(url_for('login', email=email))  # Redirect to login page

        # Validate phone number and Aadhar number
        if len(phone) != 10:
            flash("Phone number must be 10 digits.")
            return render_template("register.html")
        if len(aadhar_number) != 12:
            flash("Aadhar number must be 12 digits.")
            return render_template("register.html")

        # Insert the new user into the database
        cursor.execute(
            "INSERT INTO users (full_name, email, password, phone, address, aadhar_number, pan_card) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
            (full_name, email, password, phone, address, aadhar_number, pan_card)
        )
        conn.commit()
        cursor.close()
        conn.close()

        user_data = {
            'full_name': full_name,
            'email': email,
        }
        session['user'] = user_data
        flash("Registration successful! Please log in.")
        return redirect(url_for('confirm', user=user_data))

    return render_template("register.html")

@app.route("/confirm")
def confirm():
    user = session.get('user')
    return render_template("confirm.html", user=user)

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify login credentials
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            user_data = {
                'fullname': user[0],
                'email': user[1],
                'user_id': user[2]
            }
            session['user'] = user_data
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password!")
            return redirect(url_for('login'))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    user = session.get('user')
    if user:
        return render_template("dashboard.html", user=user)
    else:
        return redirect(url_for('login'))

@app.route("/deposit", methods=['POST', 'GET'])
def deposit():
    user_data = session.get('user')
    if user_data:
        if request.method == 'POST':
            amount = float(request.form['deposit_amount'])
            account_type = request.form['account_type']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM accounts WHERE user_id = %s", (user_data['user_id'],))
            if not cursor.fetchone():
                # Insert a new row
                cursor.execute("INSERT INTO accounts (user_id, balance, account_type) VALUES (%s, %s, %s)", (user_data['user_id'], amount, account_type))
                cursor.execute("INSERT INTO account_statements (user_id, transaction_type, transaction_amount, transaction_date) VALUES (%s, 'Credit', %s, %s)", (user_data['user_id'], amount, datetime.now()))
            else:
                # Update the existing row
                cursor.execute("UPDATE accounts SET balance = balance + %s WHERE user_id = %s", (amount, user_data['user_id']))
                cursor.execute("INSERT INTO account_statements (user_id, transaction_type, transaction_amount, transaction_date) VALUES (%s, 'Credit', %s, %s)", (user_data['user_id'], amount, datetime.now()))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Funds deposited successfully!")
            return redirect(url_for('dashboard'))
        return render_template("deposit.html")
    else:
        return redirect(url_for('login'))

@app.route("/balance", methods=['GET'])
def balance():
    user_data = session.get('user')
    if user_data:
        email = user_data['email']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM accounts WHERE user_id = %s", (user_data['user_id'],))
        balance = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return render_template("balance.html", balance=balance)
    else:
        return redirect(url_for('login'))

@app.route("/account-statement", methods=['GET'])
def account_statement():
    user_data = session.get('user')
    if user_data:
        email = user_data['email']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM account_statements WHERE user_id = %s", (user_data['user_id'],))
        transactions = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("account_statement.html", transactions=transactions)
    else:
        return redirect(url_for('login'))

@app.route("/users")
def user_details():
    user_data = session.get('user')
    if user_data:
        user_id = user_data['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()
        # Query to fetch user details from the database
        query = """
        SELECT full_name, email, phone, aadhar_number, password, pan_card 
        FROM users 
        WHERE user_id = %s
        """
        cursor.execute(query, (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        if user_data:
            user = {
                'full_name': user_data[0],
                'email': user_data[1],
                'phone': user_data[2],
                'aadhar_number': user_data[3],
                'password': user_data[4],
                'pan_card': user_data[5]
            }
            return render_template("users.html", user=user)
        else:
            return "User not found"
    else:
        return "You are not logged in"

@app.route("/transfer", methods=['POST', 'GET'])
def transfer():
    user_data = session.get('user')
    if user_data:
        if request.method == 'POST':
            recipient_user_id = request.form.get('user_id')
            amount = request.form.get('amount')
            if recipient_user_id and amount:
                try:
                    amount = float(amount)
                    # Check if the recipient user_id exists
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (recipient_user_id,))
                    recipient = cursor.fetchone()
                    if recipient is None:
                        flash("Recipient user not found!")
                        return redirect(url_for('transfer'))
