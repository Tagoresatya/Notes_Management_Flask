# app.py
# Complete Flask app with registration, login, and private notes (CRUD).
# Comments below explain every step for a beginner.

from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_mail import Mail,Message
import mysql.connector
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
import os



# --------------------
# App Initialization
# --------------------
app = Flask(__name__)
app.secret_key = "myverysecretkey"  # change this in production

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

app.config['MAIL_DEFAULT_SENDER'] = 'tagoresatya2022@gmail.com'

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# --------------------
# Database Connection Helper
# --------------------
# def get_db_connection():
    # """
    # Create and return a new MySQL connection.
    # Edit host/user/password/database if yours are different.
    # """
    # conn = mysql.connector.connect(
    #     host="localhost",
        # user="root",       # change if your MySQL username is different
        # password="Satya@#1014",       # enter MySQL password if you have one
        # database="Notes_Management" # the DB created from the SQL script above
    # )
    # return conn


def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQLHOST", "localhost"),
        user=os.getenv("MYSQLUSER", "root"),
        password=os.getenv("MYSQLPASSWORD", "Satya@#1014"),
        database=os.getenv("MYSQLDATABASE", "Notes_Management"),
        port=int(os.getenv("MYSQLPORT", 3306))
    )
    return conn




# --------------------
# Home (redirect)
# --------------------
@app.route('/')
def home():
    # If logged in -> show notes, else -> show login
    if 'user_id' in session:
        return redirect('/viewall')
    return redirect('/login')

# --------------------
# Register Route
# --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    # If POST -> process registration form
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        # Basic checks (non-empty)
        if not username or not email or not password:
            flash("Please fill all fields.", "danger")
            return redirect('/register')

        # Hash the password before saving
        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if username already exists
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        exists = cur.fetchone()
        if exists:
            # Close connection and inform user
            cur.close()
            conn.close()
            flash("Username already taken. Choose another.", "danger")
            return redirect('/register')

        # Insert new user into users table
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_pw))
        conn.commit()
        cur.close()
        conn.close()

        flash("Registration successful! You can now log in.", "success")
        return redirect('/login')

    # If GET -> show registration form
    return render_template('register.html')


@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():

    if request.method == 'POST':

        email = request.form['email']

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:

            token = serializer.dumps(
                email,
                salt='password-reset'
            )

            reset_link = url_for(
                'reset_password',
                token=token,
                _external=True
            )

            msg = Message(
                'Password Reset Request',
                recipients=[email]
            )

            msg.body = f"""
Click the link below to reset your password:

{reset_link}

This link expires in 10 minutes.
"""

            mail.send(msg)

            flash(
                'Password reset link sent to your email.',
                'success'
            )

        else:
            flash(
                'Email not found.',
                'danger'
            )

    return render_template('forgotpassword.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    try:
        email = serializer.loads(
            token,
            salt='password-reset',
            max_age=600
        )

    except:
        flash('Reset link expired.', 'danger')
        return redirect('/forgotpassword')

    if request.method == 'POST':

        password = request.form['password']

        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (hashed_pw, email)
        )

        conn.commit()

        cur.close()
        conn.close()

        flash(
            'Password updated successfully.',
            'success'
        )

        return redirect('/login')

    return render_template('resetpassword.html')

# --------------------
# Login Route
# --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If POST -> authenticate
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        # Basic check
        if not username or not password:
            flash("Please enter username and password.", "danger")
            return redirect('/login')

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        # Check whether user exists and password matches
        if user and check_password_hash(user['password'], password):
            # Save user id and username in session for future access control
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"Welcome, {user['username']}!", "success")
            return redirect('/viewall')
        else:
            flash("Invalid username or password.", "danger")
            return redirect('/login')

    # If GET -> show login page
    return render_template('login.html')

# --------------------
# Logout Route
# --------------------
@app.route('/logout')
def logout():
    # Clear session data
    session.clear()
    flash("You have been logged out.", "info")
    return redirect('/login')

# --------------------
# Add Note (CREATE)
# --------------------
@app.route('/addnote', methods=['GET', 'POST'])
def addnote():
    # Ensure user is logged in
    if 'user_id' not in session:
        flash("Please login first.", "warning")
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        user_id = session['user_id']

        if not title or not content:
            flash("Title and content cannot be empty.", "danger")
            return redirect('/addnote')

        conn = get_db_connection()
        cur = conn.cursor()
        # Save note with user_id to keep notes private
        cur.execute("INSERT INTO notes (title, content, user_id) VALUES (%s, %s, %s)",
                    (title, content, user_id))
        conn.commit()
        cur.close()
        conn.close()

        flash("Note added successfully.", "success")
        return redirect('/viewall')

    # GET -> show add note form
    return render_template('addnote.html')

# --------------------
# View All Notes (READ ALL for logged-in user)
# --------------------
@app.route('/viewall')
def viewall():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Get search text from URL
    search_query = request.args.get('search', '')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if search_query:
        cur.execute("""
            SELECT id, title, content, created_at
            FROM notes
            WHERE user_id = %s
            AND (title LIKE %s OR content LIKE %s)
            ORDER BY created_at DESC
        """, (
            user_id,
            f"%{search_query}%",
            f"%{search_query}%"
        ))
    else:
        cur.execute("""
            SELECT id, title, content, created_at
            FROM notes
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))

    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'viewnotes.html',
        notes=notes,
        search_query=search_query
    )
# --------------------
# View Single Note (READ ONE) - restricted
# --------------------
@app.route('/viewnotes/<int:note_id>')
def viewnotes(note_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    # Select note only if it belongs to current user
    cur.execute("SELECT id, title, content, created_at FROM notes WHERE id = %s AND user_id = %s", (note_id, user_id))
    note = cur.fetchone()
    cur.close()
    conn.close()

    if not note:
        # Either note doesn't exist or doesn't belong to the user
        flash("You don't have access to this note.", "danger")
        return redirect('/viewall')

    return render_template('singlenote.html', note=note)

# --------------------
# Update Note (UPDATE) - restricted
# --------------------
@app.route('/updatenote/<int:note_id>', methods=['GET', 'POST'])
def updatenote(note_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Check existence and ownership
    cur.execute("SELECT id, title, content FROM notes WHERE id = %s AND user_id = %s", (note_id, user_id))
    note = cur.fetchone()

    if not note:
        cur.close()
        conn.close()
        flash("You are not authorized to edit this note.", "danger")
        return redirect('/viewall')

    if request.method == 'POST':
        # Get updated data
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        if not title or not content:
            flash("Title and content cannot be empty.", "danger")
            return redirect(url_for('updatenote', note_id=note_id))

        # Update query guarded by user_id
        cur.execute("UPDATE notes SET title = %s, content = %s WHERE id = %s AND user_id = %s",
                    (title, content, note_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
        flash("Note updated successfully.", "success")
        return redirect('/viewall')

    # If GET -> render update form with existing note data
    cur.close()
    conn.close()
    return render_template('updatenote.html', note=note)

# --------------------
# Delete Note (DELETE) - restricted
# --------------------
@app.route('/deletenote/<int:note_id>', methods=['POST'])
def deletenote(note_id):
    # This route expects a POST request (safer than GET for delete)
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    # Delete only if the note belongs to the current user
    cur.execute("DELETE FROM notes WHERE id = %s AND user_id = %s", (note_id, user_id))
    conn.commit()
    cur.close()
    conn.close()
    flash("Note deleted.", "info")
    return redirect('/viewall')

@app.route('/home')
def about():
    return render_template('home.html')

# ---------------- CONTACT ----------------

@app.route('/contact', methods=['GET', 'POST'])
def contact():

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        msg = Message(
            subject=f'Contact Form Message from {name}',
            recipients=['tagoresatya2022@gmail.com']
        )

        msg.body = f"""
Name: {name}
Email: {email}

Message:
{message}
"""

        mail.send(msg)

        flash("Message sent successfully!", "success")
        return redirect('/contact')

    return render_template('contact.html')

# --------------------
# Run App
# --------------------
if __name__ == '__main__':
    # debug=True for development only
    app.run(debug=True)