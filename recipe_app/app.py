# app.py
import os
import psycopg2
import json
from psycopg2 import pool # Use connection pooling
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from dotenv import load_dotenv
from utils import ( # Import helpers from utils.py
    format_gemini_prompt, call_gemini_api, mock_recipe,
    validate_email, validate_password, get_substitutions
)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Ensure SECRET_KEY is set, essential for sessions
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config['SECRET_KEY']:
    print("FATAL: SECRET_KEY environment variable not set.")
    # Consider exiting or using a default ONLY for debug if absolutely necessary
    # exit() # Or raise Exception("SECRET_KEY not set")

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
        maxconn=5,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    print("Database connection pool created successfully.")
except psycopg2.OperationalError as e:
    print(f"FATAL: Could not connect to database to create pool: {e}")
    # The app might run but DB operations will fail. Consider more robust handling.

def get_db_conn():
    """Gets a connection from the pool."""
    if db_pool:
        try:
            return db_pool.getconn()
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
        except Exception as e:
             print(f"Error returning DB connection to pool: {e}")
             # If putting back fails, connection might be closed automatically or leaked
             # Consider closing it manually if appropriate conn.close()

def init_db():
    """Initializes the database (creates table if not exists)."""
    conn = get_db_conn()
    if not conn:
        print("Database connection unavailable for init.")
        return
    try:
        with conn.cursor() as cur:
            # Use IF NOT EXISTS to avoid errors if table already exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS login_details (
                    user_id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("Database table 'login_details' checked/created successfully.")
    except psycopg2.Error as e:
        print(f"Error initializing database table: {e}")
        conn.rollback() # Rollback any partial changes
    finally:
        # Always return the connection to the pool
        put_db_conn(conn)

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
            return render_template('register.html'), 400 # Bad Request

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
        conn = get_db_conn()
        if not conn:
            flash("Registration service temporarily unavailable. Please try again later.", "error")
            return render_template('register.html'), 503 # Service Unavailable

        cur = None # Initialize cursor to None
        try:
            cur = conn.cursor()
            # Check if email already exists
            cur.execute("SELECT user_id FROM login_details WHERE email = %s;", (email,))
            existing_user = cur.fetchone()

            if existing_user:
                flash("Email address already registered. Please log in.", "warning")
                # Redirect to login or show error on register page? Show on register for now.
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
            conn.rollback() # Ensure rollback on error
            print(f"Database error during registration: {e}")
            flash("An error occurred during registration. Please try again.", "error")
            return render_template('register.html'), 500 # Internal Server Error
        finally:
            if cur:
                cur.close() # Close cursor if it was opened
            put_db_conn(conn) # Return connection

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

        if not validate_email(email): # Basic check before DB query
             flash("Invalid email format.", "error")
             return render_template('login.html'), 400

        conn = get_db_conn()
        if not conn:
            flash("Login service temporarily unavailable. Please try again later.", "error")
            return render_template('login.html'), 503

        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT user_id, email, password_hash FROM login_details WHERE email = %s;", (email,))
            user = cur.fetchone() # Returns tuple or None

            if user and check_password_hash(user[2], password): # user[2] is password_hash
                # Login successful - Set up session
                session.clear() # Prevent session fixation
                session['logged_in'] = True
                session['user_id'] = user[0] # user[0] is user_id
                session['email'] = user[1]   # user[1] is email
                # session.permanent = True # Optional: Make session last longer
                flash("Login successful!", "success")
                # Redirect to home or intended destination
                return redirect(url_for('home'))
            else:
                # Invalid credentials
                flash("Invalid email or password.", "error")
                return render_template('login.html'), 401 # Unauthorized

        except psycopg2.Error as e:
            print(f"Database error during login: {e}")
            flash("An error occurred during login. Please try again.", "error")
            return render_template('login.html'), 500
        finally:
            if cur:
                cur.close()
            put_db_conn(conn)

    # For GET request or if login fails
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
    # Provide defaults and basic type checking on access
    ingredients = data.get('ingredients') if isinstance(data.get('ingredients'), list) else []
    filters = data.get('filters') if isinstance(data.get('filters'), dict) else {}
    description = data.get('description') if isinstance(data.get('description'), str) else ''

    # Format prompt and call LLM
    prompt = format_gemini_prompt(ingredients, filters, description)
    print(f"--- Sending Recipe Prompt to Gemini ---\n{prompt}\n-----------------------------")

    recipe_data = call_gemini_api(prompt) # Returns parsed JSON or None

    # Perform recipe-specific validation HERE
    if (recipe_data
            and isinstance(recipe_data, dict)
            # Check for essential keys
            and all(k in recipe_data for k in ['title', 'ingredients', 'steps'])
            # Check types of essential list fields
            and isinstance(recipe_data.get('ingredients'), list)
            and isinstance(recipe_data.get('steps'), list)
            # Check title is a non-empty string
            and isinstance(recipe_data.get('title'), str) and recipe_data['title']):

        print(f"--- Received Valid Recipe Data ---\n{json.dumps(recipe_data, indent=2)}\n---------------------------")
        # Optional: Add stateless sharing link generation here if desired
        # import base64
        # recipe_str = json.dumps(recipe_data)
        # encoded_recipe = base64.urlsafe_b64encode(recipe_str.encode()).decode()
        # share_link = url_for('shared_recipe', data=encoded_recipe, _external=True)
        # recipe_data['share_link'] = share_link
        return jsonify(recipe_data), 200 # OK
    else:
        # Log the failure reason and fallback to mock recipe
        print("--- LLM call failed or returned invalid recipe structure, using mock recipe ---")
        if recipe_data: # Log if data was received but invalid
            print(f"--- Received Data (Invalid Structure): ---\n{json.dumps(recipe_data, indent=2)}\n---------------------------")
        else: # Log if API call returned None
            print("--- Received No Data from LLM API call ---")

        mock = mock_recipe(ingredients)
        # Return mock with a different status? 200 OK might be fine if mock is acceptable UX
        return jsonify(mock), 200 # Or maybe 202 Accepted if mock is temporary


@app.route('/substitute', methods=['POST'])
def substitute_ingredient_api():
    """API endpoint for ingredient substitutions."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    ingredient = data.get('ingredient') # Expecting a string

    if not ingredient or not isinstance(ingredient, str) or not ingredient.strip():
        return jsonify({"error": "Missing or invalid 'ingredient' field"}), 400

    suggestions = get_substitutions(ingredient) # Use the updated function from utils

    # Check the result from get_substitutions to set status code
    # Use more robust checking based on the actual returned strings
    if suggestions and isinstance(suggestions, list) and len(suggestions) > 0:
        first_suggestion = suggestions[0].lower()
        if "failed" in first_suggestion or "could not be processed" in first_suggestion:
            # Return 500 if LLM failed, or maybe 503 if it implies service issue
            status_code = 500
        elif "no suggestions found" in first_suggestion or "no specific suggestions found" in first_suggestion:
            # Return 200 OK even if no suggestions, the process worked
            status_code = 200
        else:
            # Success, suggestions found
            status_code = 200
    else:
        # Should not happen based on get_substitutions logic, but handle defensively
        status_code = 500 # Internal error if list is empty or not returned correctly

    return jsonify({"ingredient": ingredient, "substitutions": suggestions}), status_code


# Optional: Route for stateless sharing (if generated in /generate)
# @app.route('/share')
# def shared_recipe():
#     # ... (Implementation for handling shared links) ...
#     pass


# --- Application Context and Teardown ---
@app.teardown_appcontext
def close_db_pool(exception=None):
    """Ensure resources tied to the app context are cleaned up if needed."""
    # *** DO NOT CLOSE THE CONNECTION POOL HERE ***
    # The pool ('db_pool') persists for the application's lifetime.
    # Individual connections obtained via get_db_conn() are returned to the pool
    # using put_db_conn() within the route handlers.

    # This function *could* be used for other context-specific cleanup,
    # but is not needed for managing the pool itself in this design.
    if exception:
         # Log any exceptions that caused the context to tear down
         print(f"App context teardown due to exception: {exception}")


# --- Main Execution ---
if __name__ == '__main__':
    if not db_pool:
         print("WARNING: Database connection pool failed to initialize during startup. DB features may fail.")
    else:
         # Initialize DB schema on startup if pool is available
         init_db()

    # Use host='0.0.0.0' to make accessible on network, default port is 5000
    # Set debug=True for development (enables auto-reloading and debugger)
    # Set debug=False for production deployment
    # Consider using environment variable for this: debug=os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    app.run(host='0.0.0.0', port=5000, debug=True)