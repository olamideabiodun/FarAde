# app.py - Main Flask Application with PostgreSQL Support
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
import datetime
from functools import wraps
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)
app.secret_key = 'happy_birthday'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3'}
PASSWORD = "02-04-2008"  
DATABASE_URL = os.environ.get('DATABASE_URL')  # For Render PostgreSQL

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Database setup
def get_db_connection():
    """Get a connection to the PostgreSQL database"""
    try:
        db_url = DATABASE_URL
        # Fix for Render PostgreSQL URL format
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://')
        
        if not db_url:
            print("ERROR: No DATABASE_URL environment variable found")
            return None
            
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def init_db():
    """Initialize the database tables if they don't exist"""
    conn = get_db_connection()
    if conn is None:
        print("Failed to initialize database: No connection")
        return
        
    try:
        cursor = conn.cursor()
        
        # Create poems table for PostgreSQL
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS poems (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL
        )
        ''')

        # Create files table for PostgreSQL
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            type TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
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
    """Load all poems from the database"""
    conn = get_db_connection()
    if conn is None:
        return []
        
    try:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM poems ORDER BY date DESC')
        poems = cursor.fetchall()
        return poems
    except Exception as e:
        print(f"Error loading poems: {e}")
        return []
    finally:
        conn.close()


def save_poem(title, content):
    """Save a new poem to the database"""
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    if conn is None:
        raise Exception("Database connection failed")
        
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO poems (title, content, date) VALUES (%s, %s, %s)',
                     (title, content, date))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving poem: {e}")
        raise e
    finally:
        conn.close()


def save_file_metadata(filename, file_path, file_type):
    """Save file metadata to the database"""
    uploaded_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    if conn is None:
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO files (name, path, type, uploaded_at) VALUES (%s, %s, %s, %s)',
                     (filename, file_path, file_type, uploaded_at))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error saving file metadata: {e}")
        return False
    finally:
        conn.close()


def load_files():
    """Load all files from the database"""
    conn = get_db_connection()
    if conn is None:
        return []
        
    try:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM files ORDER BY uploaded_at DESC')
        files = cursor.fetchall()
        return files
    except Exception as e:
        print(f"Error loading files: {e}")
        return []
    finally:
        conn.close()


def get_poem(poem_id):
    """Get a specific poem by ID"""
    conn = get_db_connection()
    if conn is None:
        return None
        
    try:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM poems WHERE id = %s', (poem_id,))
        poem = cursor.fetchone()
        return poem
    except Exception as e:
        print(f"Error getting poem: {e}")
        return None
    finally:
        conn.close()


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
        try:
            title = request.form['title']
            content = request.form['content']
            save_poem(title, content)
            flash('Your poem has been saved!')
            return redirect(url_for('poems'))
        except Exception as e:
            flash(f'Error saving poem: {str(e)}')
            return redirect(url_for('write'))
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
            if save_file_metadata(filename, file_path, file_type):
                flash('File successfully uploaded')
            else:
                flash('File uploaded but metadata could not be saved')
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
    if conn is None:
        flash('Database connection error')
        return redirect(url_for('poems'))
        
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM poems WHERE id = %s', (poem_id,))
        conn.commit()
        flash('Poem deleted successfully')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting poem: {str(e)}')
    finally:
        conn.close()
    return redirect(url_for('poems'))


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    init_db()  # Initialize the database
    # Use PORT environment variable for render.com, or default to 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)