# app.py - Main Flask Application with PostgreSQL
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
import sys
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
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Database functions
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
    print("Starting database initialization...")
    
    conn = get_db_connection()
    if conn is None:
        print("Failed to initialize database: No connection")
        return False
        
    try:
        cursor = conn.cursor()
        
        # List existing tables
        print("Checking existing tables...")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = cursor.fetchall()
        existing_tables = [table[0] for table in tables]
        print(f"Existing tables: {existing_tables}")
        
        # Create poems table
        print("Creating 'poems' table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS poems (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL
        )
        ''')

        # Create files table
        print("Creating 'files' table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            type TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        )
        ''')
        
        # Commit changes
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('poems', 'files')")
        tables = cursor.fetchall()
        final_tables = [table[0] for table in tables]
        print(f"Final tables after initialization: {final_tables}")
        
        if 'poems' in final_tables and 'files' in final_tables:
            print("Database tables created successfully!")
            return True
        else:
            print(f"ERROR: Not all tables were created. Created tables: {final_tables}")
            return False
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        return False
    finally:
        conn.close()


def check_tables_exist():
    """Check if required tables exist in the database"""
    conn = get_db_connection()
    if conn is None:
        print("Cannot check tables: No database connection")
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('poems', 'files')")
        tables = cursor.fetchall()
        existing_tables = [table[0] for table in tables]
        
        both_tables_exist = 'poems' in existing_tables and 'files' in existing_tables
        if not both_tables_exist:
            print(f"Missing tables. Found: {existing_tables}")
            # Try to initialize tables if they don't exist
            return init_db()
        return True
    except Exception as e:
        print(f"Error checking tables: {e}")
        return False
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
    if not check_tables_exist():
        print("Cannot load poems: Tables don't exist")
        return []
        
    conn = get_db_connection()
    if conn is None:
        print("Cannot load poems: No database connection")
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
    if not check_tables_exist():
        raise Exception("Database tables not initialized")
        
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    if conn is None:
        raise Exception("Database connection failed")
        
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO poems (title, content, date) VALUES (%s, %s, %s)',
                     (title, content, date))
        conn.commit()
        print(f"Poem '{title}' saved successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error saving poem: {e}")
        raise e
    finally:
        conn.close()


def save_file_metadata(filename, file_path, file_type):
    """Save file metadata to the database"""
    if not check_tables_exist():
        print("Cannot save file metadata: Tables don't exist")
        return False
        
    uploaded_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    if conn is None:
        print("Cannot save file metadata: No database connection")
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO files (name, path, type, uploaded_at) VALUES (%s, %s, %s, %s)',
                     (filename, file_path, file_type, uploaded_at))
        conn.commit()
        print(f"File metadata for '{filename}' saved successfully")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error saving file metadata: {e}")
        return False
    finally:
        conn.close()


def load_files():
    """Load all files from the database"""
    if not check_tables_exist():
        print("Cannot load files: Tables don't exist")
        return []
        
    conn = get_db_connection()
    if conn is None:
        print("Cannot load files: No database connection")
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
    if not check_tables_exist():
        print(f"Cannot get poem {poem_id}: Tables don't exist")
        return None
        
    conn = get_db_connection()
    if conn is None:
        print(f"Cannot get poem {poem_id}: No database connection")
        return None
        
    try:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM poems WHERE id = %s', (poem_id,))
        poem = cursor.fetchone()
        return poem
    except Exception as e:
        print(f"Error getting poem {poem_id}: {e}")
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
    # Check database connection on home page load
    if not check_tables_exist():
        flash('Warning: Database tables not properly initialized. Some features may not work.')
    return render_template('home.html')


@app.route('/poems')
@login_required
def poems():
    poem_list = load_poems()
    if not poem_list and not check_tables_exist():
        flash('Database tables not initialized properly. Please contact administrator.')
    return render_template('poems.html', poems=poem_list)


@app.route('/write', methods=['GET', 'POST'])
@login_required
def write():
    if request.method == 'POST':
        try:
            title = request.form['title']
            content = request.form['content']
            
            if not title or not content:
                flash('Title and content are required')
                return redirect(url_for('write'))
                
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
    file_list = load_files()
    if not file_list and not check_tables_exist():
        flash('Database tables not initialized properly. Please contact administrator.')
    return render_template('gallery.html', files=file_list)


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
            
            try:
                file.save(full_path)
                print(f"File saved to {full_path}")
                
                # Determine file type (image or video)
                file_type = 'image' if filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'} else 'video'

                # Save file metadata to database
                if save_file_metadata(filename, file_path, file_type):
                    flash('File successfully uploaded')
                else:
                    flash('File uploaded but metadata could not be saved')
                    
                return redirect(url_for('gallery'))
            except Exception as e:
                flash(f'Error uploading file: {str(e)}')
                return redirect(request.url)
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
    if not check_tables_exist():
        flash('Database tables not initialized properly. Cannot delete poem.')
        return redirect(url_for('poems'))
        
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


@app.route('/init-db')
@login_required
def initialize_db_route():
    """Route to manually initialize the database"""
    success = init_db()
    if success:
        flash('Database initialized successfully!')
    else:
        flash('Database initialization failed. Check logs for details.')
    return redirect(url_for('home'))


@app.route('/db-status')
@login_required
def db_status():
    """Route to check database status (for debugging)"""
    status = {}
    
    # Check database connection
    conn = get_db_connection()
    status['connection'] = 'OK' if conn else 'FAILED'
    
    if conn:
        try:
            # Check if tables exist
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            tables = cursor.fetchall()
            status['tables'] = [table[0] for table in tables]
            
            # Check row counts
            table_counts = {}
            for table in status['tables']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
            status['row_counts'] = table_counts
            
            conn.close()
        except Exception as e:
            status['error'] = str(e)
    
    return render_template('db_status.html', status=status)




# Run initialization if this script is run directly
if __name__ == '__main__':
    # Initialize database first
    print("Initializing database...")
    init_db()
    
    # Use PORT environment variable for render.com, or default to 8080
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting Flask app on port {port}...")
    app.run(debug=False, host='0.0.0.0', port=port)