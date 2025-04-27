# app.py
import os
import psycopg2
import json
import base64 # For sharing feature
from psycopg2 import pool # Use connection pooling
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from dotenv import load_dotenv
# Assuming utils.py contains the necessary functions (format_gemini_prompt, call_gemini_api, etc.)
from utils import (
    format_gemini_prompt, call_gemini_api, mock_recipe,
    validate_email, validate_password, get_substitutions
)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Ensure SECRET_KEY is set, essential for sessions
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config['SECRET_KEY']:
    print("FATAL: SECRET_KEY environment variable not set. Sessions will not work.")
    # In a real app, you might raise an exception or exit here
    # raise ValueError("SECRET_KEY environment variable is required for session management.")

# --- Database Configuration ---
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# Database Connection Pooling
db_pool = None # Initialize to None
try:
    # Use minconn=1, maxconn=5 or adjust based on expected load
    db_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10, # Increased max connections slightly
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        # Keepalive settings can help prevent connection drops on idle networks
        # keepalives=1,
        # keepalives_idle=30,
        # keepalives_interval=10,
        # keepalives_count=5
    )
    print("Database connection pool created successfully.")
except psycopg2.OperationalError as e:
    print(f"FATAL: Could not connect to database to create pool: {e}")
    # The app might run but DB operations will fail.
except Exception as e:
    print(f"FATAL: An unexpected error occurred creating the DB pool: {e}")


# --- DB Helper Functions ---
def get_db_conn():
    """Gets a connection from the pool."""
    if db_pool:
        try:
            conn = db_pool.getconn()
            if conn:
                # print("DEBUG: Acquired DB connection from pool.") # Optional debug log
                return conn
            else:
                print("Error: db_pool.getconn() returned None.")
                return None
        except Exception as e:
            print(f"Error getting DB connection from pool: {e}")
            return None
    print("DB connection pool is not available.")
    return None

def put_db_conn(conn):
    """Returns a connection to the pool."""
    if db_pool and conn:
        try:
             db_pool.putconn(conn)
             # print("DEBUG: Returned DB connection to pool.") # Optional debug log
        except Exception as e:
             print(f"Error returning DB connection to pool: {e}")
             # If putting back fails, try closing it to prevent leaks
             try:
                 conn.close()
             except Exception as close_e:
                 print(f"Error closing connection after putconn failed: {close_e}")


def init_db():
    """Initializes the database (creates table if not exists)."""
    conn = get_db_conn()
    if not conn:
        print("Database connection unavailable for init_db.")
        return False # Indicate failure
    created = False
    try:
        with conn.cursor() as cur:
            print("DEBUG: Attempting to create login_details table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS login_details (
                    user_id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Optionally check if table exists after attempting creation for confirmation
            # cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'login_details');")
            # table_exists = cur.fetchone()[0]
            # if table_exists:
            #     print("Database table 'login_details' checked/created successfully.")
            #     created = True
            # else:
            #     print("ERROR: login_details table check failed after CREATE IF NOT EXISTS.")

            conn.commit() # Commit the transaction
            print("Database table 'login_details' checked/created successfully (commit executed).")
            created = True

    except psycopg2.Error as e:
        print(f"Error initializing database table: {e}")
        conn.rollback() # Rollback any partial changes
    except Exception as e:
        print(f"Unexpected error during init_db: {e}")
        conn.rollback()
    finally:
        put_db_conn(conn) # Always return the connection
    return created

# --- Routes ---

@app.route('/')
def home():
    """Main application page. Allows access even if not logged in."""
    return render_template('index.html', logged_in=session.get('logged_in', False))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if session.get('logged_in'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Server-side Validation
        if not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template('register.html'), 400

        if not validate_email(email):
            flash("Invalid email format.", "error")
            return render_template('register.html'), 400

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('register.html'), 400

        is_valid_pw, pw_error_msg = validate_password(password)
        if not is_valid_pw:
            flash(pw_error_msg, "error")
            return render_template('register.html'), 400

        # Database Interaction
        conn = None # Ensure conn is defined outside try
        cur = None # Ensure cur is defined outside try
        try:
            conn = get_db_conn()
            if not conn:
                flash("Registration service temporarily unavailable [DB Pool Error]. Please try again later.", "error")
                return render_template('register.html'), 503

            cur = conn.cursor()
            # Check if email already exists
            cur.execute("SELECT user_id FROM login_details WHERE email = %s;", (email,))
            existing_user = cur.fetchone()

            if existing_user:
                flash("Email address already registered. Please log in.", "warning")
                return render_template('register.html'), 409 # Conflict

            # Hash password and insert new user
            hashed_password = generate_password_hash(password)
            cur.execute(
                "INSERT INTO login_details (email, password_hash) VALUES (%s, %s);",
                (email, hashed_password)
            )
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))

        except psycopg2.Error as e:
            if conn: conn.rollback() # Rollback only if connection exists
            print(f"Database error during registration: {e}")
            flash("An error occurred during registration. Please try again.", "error")
            # Check for specific errors if needed (e.g., unique constraint violation if check failed somehow)
            return render_template('register.html'), 500 # Internal Server Error
        except Exception as e:
            if conn: conn.rollback()
            print(f"Unexpected error during registration: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
            return render_template('register.html'), 500
        finally:
            if cur:
                cur.close()
            if conn:
                put_db_conn(conn)

    # For GET request
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if session.get('logged_in'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template('login.html'), 400

        if not validate_email(email): # Basic format check
             flash("Invalid email format.", "error")
             return render_template('login.html'), 400

        conn = None
        cur = None
        try:
            conn = get_db_conn()
            if not conn:
                flash("Login service temporarily unavailable [DB Pool Error]. Please try again later.", "error")
                return render_template('login.html'), 503

            cur = conn.cursor()
            cur.execute("SELECT user_id, email, password_hash FROM login_details WHERE email = %s;", (email,))
            user = cur.fetchone() # Returns tuple (id, email, hash) or None

            if user and check_password_hash(user[2], password): # user[2] is password_hash
                # Login successful - Set up session
                session.clear() # Prevent session fixation attacks
                session['logged_in'] = True
                session['user_id'] = user[0] # user[0] is user_id
                session['email'] = user[1]   # user[1] is email
                # session.permanent = True # Optional: Make session last longer than browser close
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                # Invalid credentials
                flash("Invalid email or password.", "error")
                return render_template('login.html'), 401 # Unauthorized

        except psycopg2.Error as e:
            print(f"Database error during login: {e}")
            flash("An error occurred during login. Please try again.", "error")
            return render_template('login.html'), 500
        except Exception as e:
            print(f"Unexpected error during login: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
            return render_template('login.html'), 500
        finally:
            if cur:
                cur.close()
            if conn:
                put_db_conn(conn)

    # For GET request or if login fails/validation fails
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.clear() # Clears all session data
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# --- API Endpoints ---

@app.route('/generate', methods=['POST'])
def generate_recipe_api():
    """API endpoint to generate recipes using LLM."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    ingredients = data.get('ingredients') if isinstance(data.get('ingredients'), list) else []
    filters = data.get('filters') if isinstance(data.get('filters'), dict) else {}
    description = data.get('description') if isinstance(data.get('description'), str) else ''

    prompt = format_gemini_prompt(ingredients, filters, description)
    print(f"--- Sending Recipe Prompt to Gemini ---") # Avoid logging full prompt if sensitive

    recipe_data = call_gemini_api(prompt) # Returns parsed JSON or None

    # Perform recipe-specific validation
    if (recipe_data
            and isinstance(recipe_data, dict)
            and all(k in recipe_data for k in ['title', 'ingredients', 'steps'])
            and isinstance(recipe_data.get('ingredients'), list)
            and isinstance(recipe_data.get('steps'), list)
            and isinstance(recipe_data.get('title'), str) and recipe_data['title'].strip()):

        print(f"--- Received Valid Recipe Data ---")
        return jsonify(recipe_data), 200 # OK
    else:
        print("--- LLM call failed or returned invalid recipe structure, using mock recipe ---")
        if recipe_data:
            print(f"--- Received Data (Invalid Structure): {json.dumps(recipe_data, indent=2)} ---")
        else:
            print("--- Received No Data from LLM API call ---")
        mock = mock_recipe(ingredients)
        return jsonify(mock), 200 # Return mock recipe with 200 OK status


@app.route('/substitute', methods=['POST'])
def substitute_ingredient_api():
    """API endpoint for ingredient substitutions."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    ingredient = data.get('ingredient')

    if not ingredient or not isinstance(ingredient, str) or not ingredient.strip():
        return jsonify({"error": "Missing or invalid 'ingredient' field"}), 400

    suggestions = get_substitutions(ingredient) # Uses the function from utils

    # Determine status code based on suggestion result
    status_code = 200 # Default OK
    if suggestions and isinstance(suggestions, list) and len(suggestions) > 0:
        first_suggestion_lower = suggestions[0].lower()
        # Check for failure messages returned by get_substitutions
        if "failed" in first_suggestion_lower or "could not be processed" in first_suggestion_lower:
             status_code = 500 # Indicate internal error if suggestion failed
    elif not suggestions or not isinstance(suggestions, list):
         # Should not happen if get_substitutions behaves, but handle defensively
         status_code = 500
         suggestions = ["Error processing substitution request."] # Provide error message

    return jsonify({"ingredient": ingredient, "substitutions": suggestions}), status_code


# --- Recipe Sharing Route ---

@app.route('/share')
def shared_recipe():
    """Handles incoming shared recipe links (Stateless)."""
    encoded_data = request.args.get('data')

    if not encoded_data:
        flash("Invalid or missing share data in the link.", "warning")
        return redirect(url_for('home'))

    try:
        # Decode URL-safe Base64 data
        # Need to add padding back if it was stripped during JS encoding
        # Python's urlsafe_b64decode often handles this, but manual padding can be safer
        missing_padding = len(encoded_data) % 4
        if missing_padding:
            encoded_data += '=' * (4 - missing_padding)

        decoded_bytes = base64.urlsafe_b64decode(encoded_data)
        decoded_str = decoded_bytes.decode('utf-8')

        # Parse the JSON string back into a recipe object
        recipe_data = json.loads(decoded_str)

        # Basic validation of the decoded data structure
        if not isinstance(recipe_data, dict) or not all(k in recipe_data for k in ['title', 'ingredients', 'steps']):
             flash("Shared link contains invalid recipe data.", "error")
             return redirect(url_for('home'))

        # Render the main template, passing the recipe data
        print(f"Displaying shared recipe via URL: {recipe_data.get('title', 'Untitled')}")
        return render_template('index.html',
                               shared_recipe=recipe_data, # Pass data to template
                               logged_in=session.get('logged_in', False)) # Maintain login status view

    except (base64.binascii.Error, ValueError) as e:
        print(f"Error decoding Base64 share data: {e}. Input: {encoded_data[:50]}...") # Log partial input
        flash("Could not decode the shared recipe link. It might be incomplete or corrupted.", "error")
        return redirect(url_for('home'))
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from shared data: {e}")
        flash("Could not read the shared recipe data format.", "error")
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Unexpected error handling shared link: {e}")
        flash("An unexpected error occurred loading the shared recipe.", "error")
        return redirect(url_for('home'))


# --- Application Context Teardown ---
@app.teardown_appcontext
def handle_app_context_teardown(exception=None):
    """Placeholder for any request-specific cleanup if needed."""
    # *** DO NOT CLOSE THE DB POOL HERE ***
    # Connections are returned to the pool via put_db_conn() in routes.
    # Pool is managed globally for the app's lifetime.
    if exception:
         # Log any exceptions that caused the context to tear down abnormally
         print(f"App context teardown triggered by exception: {exception}")


# --- Main Execution ---
if __name__ == '__main__':
    # Attempt to initialize DB schema only if the pool was created
    if db_pool:
        init_success = init_db()
        if not init_success:
             print("WARNING: Database initialization failed. Table 'login_details' might be missing.")
    else:
         print("WARNING: Database connection pool is unavailable. DB features will fail.")

    # Determine debug mode from environment variable or default to True for development
    # Set FLASK_DEBUG=0 or FLASK_ENV=production in .env for production
    debug_mode = os.getenv('FLASK_DEBUG', '1').lower() in ['true', '1', 't', 'yes', 'on']
    print(f"Starting Flask app with debug mode: {debug_mode}")

    # Use host='0.0.0.0' to make accessible on network
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)

    # Code here will run after the server stops (e.g., Ctrl+C)
    # Proper place to close the pool if needed, though Python exit usually handles it
    # print("Flask server shutting down. Closing DB pool.")
    # if db_pool:
    #     db_pool.closeall()