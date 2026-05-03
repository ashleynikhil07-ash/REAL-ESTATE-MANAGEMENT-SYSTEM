from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "realestate_secret_key"

# ---------------- DATABASE ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="welcome2nikhil",
    database="real_estate"
)

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template("login.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    cursor = db.cursor()
    cursor.execute("SELECT role FROM users WHERE username=%s AND password=%s", (username, password))
    result = cursor.fetchone()

    if result:
        session['username'] = username
        session['role'] = result[0]

        if result[0] == 'admin':
            return redirect('/admin')
        elif result[0] == 'agent':
            return redirect('/agent')
        elif result[0] == 'buyer':
            return redirect('/buyer')
    else:
        return "Invalid Login"

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return "Access Denied"
    return render_template("admin_dashboard.html")

# ---------------- ADD PROPERTY ----------------
@app.route('/add_property', methods=['GET', 'POST'])
def add_property():
    if session.get('role') != 'admin':
        return "Access Denied"

    if request.method == 'POST':
        title = request.form['title']
        location = request.form['location']
        price = request.form['price']
        property_type = request.form['property_type']
        image_url = request.form['image_url']
        
        cursor = db.cursor()
        cursor.execute("""
INSERT INTO property (title, location, price, property_type, image_url)
VALUES (%s, %s, %s, %s, %s)
""", (title, location, price, property_type, image_url))

        db.commit()
        return redirect('/view_properties')

    return render_template("add_property.html")

# ---------------- VIEW PROPERTIES ----------------
@app.route('/view_properties')
def view_properties():
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()
    cursor.execute("SELECT * FROM property")
    properties = cursor.fetchall()

    return render_template("view_properties.html", properties=properties)

# ---------------- AGENT DASHBOARD ----------------
@app.route('/agent')
def agent():
    if session.get('role') != 'agent':
        return "Access Denied"

    cursor = db.cursor()

    # Total appointments
    cursor.execute("SELECT COUNT(*) FROM appointment WHERE agent_name=%s", (session['username'],))
    total = cursor.fetchone()[0]

    # Successful visits
    cursor.execute("SELECT COUNT(*) FROM appointment WHERE agent_name=%s AND visit_status='Success'", (session['username'],))
    success = cursor.fetchone()[0]

    # Pending visits
    cursor.execute("SELECT COUNT(*) FROM appointment WHERE agent_name=%s AND visit_status='Pending'", (session['username'],))
    pending = cursor.fetchone()[0]

    return render_template("agent_dashboard.html", total=total, success=success, pending=pending)

# ---------------- AGENT PROPERTIES ----------------
@app.route('/agent_properties')
def agent_properties():
    if session.get('role') != 'agent':
        return "Access Denied"

    cursor = db.cursor()
    cursor.execute("SELECT * FROM property")
    properties = cursor.fetchall()

    return render_template("agent_properties.html", properties=properties)

# ---------------- AGENT APPOINTMENTS ----------------
@app.route('/agent_appointments')
def agent_appointments():
    if session.get('role') != 'agent':
        return "Access Denied"

    cursor = db.cursor()
    cursor.execute("SELECT * FROM appointment")
    appointments = cursor.fetchall()

    return render_template("agent_appointments.html", appointments=appointments)

# ---------------- UPDATE STATUS ----------------
@app.route('/update_status/<int:id>/<status>')
def update_status(id, status):
    if session.get('role') != 'agent':
        return "Access Denied"

    cursor = db.cursor()
    cursor.execute("UPDATE appointment SET visit_status=%s WHERE appointment_id=%s", (status, id))
    db.commit()

    return redirect('/agent_appointments')

# ---------------- BUYER DASHBOARD ----------------
@app.route('/buyer')
def buyer():
    if session.get('role') != 'buyer':
        return "Access Denied"
    return render_template("buyer_dashboard.html")

# ---------------- BROWSE PROPERTIES ----------------
@app.route('/browse_properties')
def browse_properties():
    if session.get('role') != 'buyer':
        return "Access Denied"

    location = request.args.get('location')
    max_price = request.args.get('price')
    sort = request.args.get('sort')

    cursor = db.cursor()

    query = "SELECT * FROM property WHERE status='Available'"
    values = []
 

    if location:
        query += " AND location LIKE %s"
        values.append(f"%{location}%")

    if max_price:
        query += " AND price <= %s"
        values.append(max_price)

    if sort == "low":
        query += " ORDER BY price ASC"
    elif sort == "high":
        query += " ORDER BY price DESC"

    cursor.execute(query, tuple(values))
    properties = cursor.fetchall()

    return render_template("browse_properties.html", properties=properties)

# ---------------- BOOK APPOINTMENT ----------------
@app.route('/book/<int:property_id>', methods=['GET', 'POST'])
def book_appointment(property_id):
    if session.get('role') != 'buyer':
        return "Access Denied"

    if request.method == 'POST':
        visit_date = request.form['visit_date']
        buyer_name = session['username']

        cursor = db.cursor()

        # Get all agents
        cursor.execute("SELECT username FROM users WHERE role='agent' ORDER BY username")
        agents = cursor.fetchall()

        # Count total appointments
        cursor.execute("SELECT COUNT(*) FROM appointment")
        count = cursor.fetchone()[0]

        if agents:
            agent_index = count % len(agents)
            agent_name = agents[agent_index][0]
            print("Assigned Agent:", agent_name)
        else:
            return "No agents available!"

        # Insert appointment
        cursor.execute("""
            INSERT INTO appointment (buyer_name, property_id, visit_date, agent_name, visit_status)
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (buyer_name, property_id, visit_date, agent_name))

        db.commit()
        return render_template("booking_success.html")

    return render_template("book_appointment.html", property_id=property_id)
# ---------------- MARK SOLD ----------------
@app.route('/mark_sold/<int:id>')
def mark_sold(id):
    if session.get('role') not in ['admin', 'agent']:
        return "Access Denied"

    cursor = db.cursor()
    cursor.execute("UPDATE property SET status='Sold' WHERE property_id=%s", (id,))
    db.commit()

    return redirect('/view_properties')

# ---------------- REPORTS ----------------
@app.route('/reports')
def reports():
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM property")
    total_properties = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM property WHERE status='Sold'")
    total_sold = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM property WHERE status='Available'")
    total_available = cursor.fetchone()[0]

    return render_template("reports.html",
                           total_properties=total_properties,
                           total_sold=total_sold,
                           total_available=total_available)

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = 'buyer'

        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing = cursor.fetchone()

        if existing:
            return "Username already exists!"

        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, %s)
        """, (username, password, role))

        db.commit()
        return redirect('/')

    return render_template("register.html")

# ---------------- ADD AGENT ----------------
@app.route('/add_agent', methods=['GET', 'POST'])
def add_agent():
    if session.get('role') != 'admin':
        return "Access Denied"

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor()

        # 🔥 Check if agent already exists
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        existing = cursor.fetchone()

        if existing:
            return "Agent already exists!"

        # 🔥 Insert agent
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, 'agent')
        """, (username, password))

        db.commit()

        return redirect('/manage_agents')   # 👈 go directly to agents page

    return render_template("add_agent.html")

@app.route('/delete_property/<int:id>')
def delete_property(id):
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()

    # 🔥 STEP 1: Delete related appointments FIRST
    cursor.execute("DELETE FROM appointment WHERE property_id=%s", (id,))

    # 🔥 STEP 2: Then delete property
    cursor.execute("DELETE FROM property WHERE property_id=%s", (id,))

    db.commit()

    return redirect('/view_properties')

@app.route('/edit_property/<int:id>', methods=['GET', 'POST'])
def edit_property(id):
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()

    if request.method == 'POST':
        title = request.form['title']
        location = request.form['location']
        price = request.form['price']
        property_type = request.form['property_type']
        image_url = request.form['image_url']

        cursor.execute("""
UPDATE property
SET title=%s, location=%s, price=%s, property_type=%s, image_url=%s
WHERE property_id=%s
""", (title, location, price, property_type, image_url, id))

        db.commit()
        return redirect('/view_properties')

    cursor.execute("SELECT * FROM property WHERE property_id=%s", (id,))
    property = cursor.fetchone()

    return render_template("edit_property.html", property=property)

@app.route('/manage_agents')
def manage_agents():
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()
    cursor.execute("""
    SELECT u.username,
    COALESCE(SUM(CASE WHEN a.visit_status='Success' THEN 1 ELSE 0 END), 0) AS accepted_count
    FROM users u
    LEFT JOIN appointment a 
    ON u.username = a.agent_name
    WHERE u.role='agent'
    GROUP BY u.username
""")
    agents = cursor.fetchall()

    return render_template("manage_agents.html", agents=agents)

@app.route('/delete_agent/<username>')
def delete_agent(username):
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()

    # 🔥 Remove agent reference from appointments
    cursor.execute("""
        UPDATE appointment 
        SET agent_name = 'Unassigned'
        WHERE agent_name=%s
    """, (username,))

    # 🔥 Delete agent
    cursor.execute("""
        DELETE FROM users 
        WHERE username=%s AND role='agent'
    """, (username,))

    db.commit()

    return redirect('/manage_agents')

@app.route('/agent_performance')
def agent_performance():
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()

    cursor.execute("""
        SELECT u.username,
        COALESCE(SUM(CASE WHEN a.visit_status='Success' THEN 1 ELSE 0 END), 0) AS success,
        COALESCE(SUM(CASE WHEN a.visit_status='Rejected' THEN 1 ELSE 0 END), 0) AS rejected,
        COALESCE(SUM(CASE WHEN a.visit_status='Success' THEN 1000 ELSE 0 END), 0) AS commission
        FROM users u
        LEFT JOIN appointment a 
        ON u.username = a.agent_name
        WHERE u.role='agent'
        GROUP BY u.username
        ORDER BY success DESC
    """)

    data = cursor.fetchall()

    return render_template("agent_performance.html", data=data)

@app.route('/add_sale', methods=['GET', 'POST'])
def add_sale():
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()

    if request.method == 'POST':
        buyer_name = request.form['buyer_name']
        property_id = request.form['property_id']
        agent_name = request.form['agent_name']
        sale_price = request.form['sale_price']
        sale_date = request.form['sale_date']

        # Insert into sales table
        cursor.execute("""
            INSERT INTO sales (buyer_name, property_id, agent_name, sale_price, sale_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (buyer_name, property_id, agent_name, sale_price, sale_date))

        # Mark property as sold
        cursor.execute("""
            UPDATE property SET status='Sold' WHERE property_id=%s
        """, (property_id,))

        db.commit()

        return redirect('/reports')

    # Get dropdown data
    cursor.execute("SELECT username FROM users WHERE role='buyer'")
    buyers = cursor.fetchall()

    cursor.execute("SELECT property_id, title FROM property WHERE status='Available'")
    properties = cursor.fetchall()

    cursor.execute("SELECT username FROM users WHERE role='agent'")
    agents = cursor.fetchall()

    return render_template("add_sale.html", buyers=buyers, properties=properties, agents=agents)


@app.route('/sales_dashboard')
def sales_dashboard():
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()

    # ✅ TOTAL SALES
    cursor.execute("SELECT COUNT(*) FROM payments")
    total_sales = cursor.fetchone()[0]

    # ✅ TOTAL REVENUE
    cursor.execute("SELECT COALESCE(SUM(amount),0) FROM payments")
    total_revenue = cursor.fetchone()[0]

    # ✅ TOP AGENT
    cursor.execute("""
        SELECT agent_name, COUNT(*) as total
        FROM payments
        GROUP BY agent_name
        ORDER BY total DESC
        LIMIT 1
    """)
    top_agent = cursor.fetchone()

    # ✅ RECENT SALES
    cursor.execute("""
        SELECT buyer_name, property_id, agent_name, amount, payment_date
        FROM payments
        ORDER BY payment_date DESC
    """)
    sales = cursor.fetchall()

    return render_template("sales_dashboard.html",
                           total_sales=total_sales,
                           total_revenue=total_revenue,
                           top_agent=top_agent,
                           sales=sales)

@app.route('/property/<int:id>')
def property_detail(id):
    if session.get('role') != 'buyer':
        return "Access Denied"

    cursor = db.cursor()
    cursor.execute("SELECT * FROM property WHERE property_id=%s", (id,))
    property = cursor.fetchone()

    return render_template("property_detail.html", property=property)


@app.route('/payment/<int:property_id>', methods=['GET', 'POST'])
def payment(property_id):
    if session.get('role') != 'buyer':
        return "Access Denied"

    cursor = db.cursor()

    # GET PROPERTY
    cursor.execute("SELECT * FROM property WHERE property_id=%s", (property_id,))
    property = cursor.fetchone()

    if request.method == 'POST':

        buyer_name = session['username']
        amount = property[3]
        method = request.form['method']

        # GET AGENTS
        cursor.execute("SELECT username FROM users WHERE role='agent'")
        agents = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM payments")
        count = cursor.fetchone()[0]

        if agents:
            agent_name = agents[count % len(agents)][0]
        else:
            agent_name = "Unassigned"

        # INSERT PAYMENT (🔥 INSIDE IF)
        cursor.execute("""
        INSERT INTO payments (buyer_name, property_id, amount, payment_method, payment_date, agent_name)
        VALUES (%s, %s, %s, %s, CURDATE(), %s)
        """, (buyer_name, property_id, amount, method, agent_name))

        # UPDATE PROPERTY
        cursor.execute("""
        UPDATE property SET status='Sold'
        WHERE property_id=%s
        """, (property_id,))

        db.commit()

        return render_template("payment_success.html", agent=agent_name)

    # 🔥 THIS RUNS FOR GET REQUEST
    return render_template("payment.html", property=property)

@app.route('/payments')
def view_payments():
    if session.get('role') != 'admin':
        return "Access Denied"

    cursor = db.cursor()
    cursor.execute("SELECT * FROM payments")
    data = cursor.fetchall()

    return render_template("payments.html", data=data)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
