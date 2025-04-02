# app.py - Main Flask Application with SQLite
from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.urls import quote as url_quote
from werkzeug.utils import secure_filename
import os
import sqlite3
import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'FarAde'

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3'}
PASSWORD = "02-04-2008"
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'birthday_website.db')

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Database setup
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create poems table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS poems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        date TEXT NOT NULL
    )
    ''')

    # Create files table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        path TEXT NOT NULL,
        type TEXT NOT NULL,
        uploaded_at TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()


# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def load_poems():
    conn = get_db_connection()
    poems = conn.execute('SELECT * FROM poems ORDER BY date DESC').fetchall()
    conn.close()
    return poems


def save_poem(title, content):
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute('INSERT INTO poems (title, content, date) VALUES (?, ?, ?)',
                 (title, content, date))
    conn.commit()
    conn.close()


def save_file_metadata(filename, file_path, file_type):
    uploaded_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute('INSERT INTO files (name, path, type, uploaded_at) VALUES (?, ?, ?, ?)',
                 (filename, file_path, file_type, uploaded_at))
    conn.commit()
    conn.close()


def load_files():
    conn = get_db_connection()
    files = conn.execute('SELECT * FROM files ORDER BY uploaded_at DESC').fetchall()
    conn.close()
    return files


def get_poem(poem_id):
    conn = get_db_connection()
    poem = conn.execute('SELECT * FROM poems WHERE id = ?', (poem_id,)).fetchone()
    conn.close()
    return poem


# Routes
@app.route('/')
def login():
    if 'logged_in' in session:
        return redirect(url_for('home'))
    return render_template('login.html')


@app.route('/check_password', methods=['POST'])
def check_password():
    if request.form['password'] == PASSWORD:
        session['logged_in'] = True
        return redirect(url_for('home'))
    flash('Incorrect password! Try again.')
    return redirect(url_for('login'))


@app.route('/home')
@login_required
def home():
    return render_template('home.html')


@app.route('/poems')
@login_required
def poems():
    return render_template('poems.html', poems=load_poems())


@app.route('/write', methods=['GET', 'POST'])
@login_required
def write():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        save_poem(title, content)
        flash('Your poem has been saved!')
        return redirect(url_for('poems'))
    return render_template('write.html')


@app.route('/gallery')
@login_required
def gallery():
    return render_template('gallery.html', files=load_files())


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join('uploads', filename)
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(full_path)

            # Determine file type (image or video)
            file_type = 'image' if filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'} else 'video'

            # Save file metadata to database
            save_file_metadata(filename, file_path, file_type)

            flash('File successfully uploaded')
            return redirect(url_for('gallery'))
        else:
            flash('File type not allowed')
            return redirect(request.url)

    return render_template('upload.html')


@app.route('/poem/<int:poem_id>')
@login_required
def view_poem(poem_id):
    poem = get_poem(poem_id)
    if not poem:
        flash('Poem not found')
        return redirect(url_for('poems'))
    return render_template('view_poem.html', poem=poem)


@app.route('/poem/delete/<int:poem_id>', methods=['POST'])
@login_required
def delete_poem(poem_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM poems WHERE id = ?', (poem_id,))
    conn.commit()
    conn.close()
    flash('Poem deleted successfully')
    return redirect(url_for('poems'))


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    init_db()  # Initialize the database
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)