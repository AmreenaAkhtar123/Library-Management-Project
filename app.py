import mysql.connector
from flask import Flask, render_template, request, redirect, session, url_for
app = Flask(__name__)
app.secret_key = 'lib@2025'  # Needed for session


def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="prosql.com123",
        database="libdb"
    )


@app.route('/dashboard')
def dashboard_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('index.html')


@app.route('/')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')


    conn = connect_db()
    cursor = conn.cursor()

    # Total books
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    # Total members
    cursor.execute("SELECT COUNT(*) FROM member")
    total_members = cursor.fetchone()[0]

    # Currently borrowed books (return_date is NULL)
    cursor.execute("SELECT COUNT(*) FROM borrowings WHERE return_date IS NULL")
    books_borrowed = cursor.fetchone()[0]

    # Books issued today
    cursor.execute("SELECT COUNT(*) FROM borrowings WHERE DATE(borrow_date) = CURDATE()")
    books_today = cursor.fetchone()[0]

    conn.close()

    return render_template('index.html', total_books=total_books, total_members=total_members, books_borrowed=books_borrowed, books_today=books_today)


@app.route('/register', methods=['GET', 'POST'])
def register_member():
    if 'user_id' not in session:
        return redirect('/login')

    conn = connect_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        try:
            cursor.execute("INSERT INTO member (name, email) VALUES (%s, %s)", (name, email))
            conn.commit()
        except mysql.connector.Error as err:
            print("❌ SQL ERROR:", err)
            return f"<h3>Error: {err}</h3>"

    # Fetch all members to display
    cursor.execute("SELECT id, name, email, registration_date FROM member")
    members = cursor.fetchall()
    conn.close()

    return render_template('RegisterMember.html', members=members)



@app.route('/manage-books', methods=['GET', 'POST'])
def manage_books():
    if 'user_id' not in session:
        return redirect('/login')

    conn = connect_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        category = request.form['category']
        quantity = request.form['quantity']

        try:
            cursor.execute("""
                INSERT INTO books (title, author, category, quantity, isbn)
                VALUES (%s, %s, %s, %s, %s)
            """, (title, author, category, quantity , isbn))
            conn.commit()
        except mysql.connector.Error as err:
            print("❌ SQL ERROR:", err)
            return f"<h3>Error: {err}</h3>"

    cursor.execute("SELECT id, title, author, category, quantity, isbn FROM books")
    books = cursor.fetchall()
    conn.close()

    return render_template('manageBooks.html', books=books)


@app.route('/borrow-return', methods=['GET', 'POST'])
def borrow_return():
    if 'user_id' not in session:
        return redirect('/login')

    conn = connect_db()
    cursor = conn.cursor()

    message = ""

    if request.method == 'POST':
        form_type = request.form['form_type']

        if form_type == 'borrow':
            member_id = request.form['member_id']
            book_id = request.form['book_id']

            # Check available quantity
            cursor.execute("SELECT quantity FROM books WHERE id = %s", (book_id,))
            result = cursor.fetchone()

            if result and result[0] > 0:
                try:
                    # Insert borrowing record
                    cursor.execute("""
                        INSERT INTO borrowings (member_id, book_id)
                        VALUES (%s, %s)
                    """, (member_id, book_id))

                    # Decrease quantity
                    cursor.execute("""
                        UPDATE books SET quantity = quantity - 1 WHERE id = %s
                    """, (book_id,))
                    conn.commit()
                    message = "✅ Book issued successfully."
                except mysql.connector.Error as err:
                    conn.rollback()
                    message = f"❌ Borrowing Error: {err}"
            else:
                message = "❌ Book not available."

        elif form_type == 'return':
            borrow_id = request.form['borrow_id']
            return_date = request.form['return_date']

            # Get book_id from borrowings
            cursor.execute("SELECT book_id FROM borrowings WHERE id = %s", (borrow_id,))
            result = cursor.fetchone()

            if result:
                book_id = result[0]
                try:
                    # Update return date
                    cursor.execute("""
                        UPDATE borrowings SET return_date = %s WHERE id = %s
                    """, (return_date, borrow_id))

                    # Increase book quantity
                    cursor.execute("""
                        UPDATE books SET quantity = quantity + 1 WHERE id = %s
                    """, (book_id,))
                    conn.commit()
                    message = "✅ Book returned successfully."
                except mysql.connector.Error as err:
                    conn.rollback()
                    message = f"❌ Return Error: {err}"
            else:
                message = "❌ Invalid borrow ID."

    conn.close()
    return render_template('BorrowReturn.html', message=message)


@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect('/login')

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            b.id, 
            m.name AS member_name, 
            bk.title AS book_title, 
            b.borrow_date, 
            b.return_date, 
            b.fine
        FROM borrowings b
        JOIN member m ON b.member_id = m.id
        JOIN books bk ON b.book_id = bk.id
        ORDER BY b.borrow_date DESC
    """)
    records = cursor.fetchall()
    conn.close()

    return render_template('Reports.html', records=records)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, role FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = username
            session['role'] = user[1]
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ✅ Only one __main__ block at the very bottom
if __name__ == '__main__':
    try:
        conn = connect_db()
        print("✅ Connected to MySQL!")
        conn.close()
    except Exception as e:
        print("❌ Connection failed:", e)

    app.run(debug=True)
