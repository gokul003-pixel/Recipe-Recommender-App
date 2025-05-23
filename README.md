# AI Recipe Recommender Web App

**Version:** 1.0 (as of April 27, 2025)

## 📖 Description

This web application allows users to generate unique recipes based on ingredients they have on hand, dietary preferences, and other criteria, leveraging the power of Google's Gemini Large Language Model (LLM). It also includes features for ingredient substitution suggestions, managing a dynamic shopping list, and sharing generated recipes.

## ✨ Features

* **AI-Powered Recipe Generation:** Enter ingredients, dietary needs (vegan, vegetarian, gluten-free etc.), cuisine style, and descriptive requests to get custom recipes generated by the Gemini API.
* **Ingredient Substitution:** Get suggestions for ingredient substitutions, using both static rules and LLM-based recommendations.
* **Dynamic Shopping List:**
    * Add ingredients directly from generated recipes.
    * Manually add/remove items.
    * Items are automatically categorized (Vegetables, Spices, etc.).
    * Check off items as you shop.
    * Persists between sessions using LocalStorage.
    * Export/Copy the list as plain text.
* **Stateless Recipe Sharing:**
    * Generate a unique shareable link for any generated recipe.
    * Share the link via direct copy, Email, Facebook, Twitter (X), and WhatsApp.
    * Uses the Web Share API for native sharing dialogs where available.
    * *Note:* Uses stateless URL encoding (Base64), so share links can be quite long.
* **User Authentication:**
    * User registration and login functionality.
    * Password hashing (via Werkzeug).
    * Session management using Flask sessions.
    * User details stored in a PostgreSQL database.
    * Option to skip login and use core recipe generation features.
* **Save Recipe:** Download the currently displayed recipe as a formatted `.txt` file.
* **Fallback Logic:** Includes a mock recipe generator if the LLM API call fails.

## 🏛️ Architecture

* **Frontend:** Vanilla JavaScript interacting directly with the backend API, managing UI updates, LocalStorage, and external sharing APIs. Uses Bootstrap for basic styling.
* **Backend:** Python Flask framework.
    * Handles API requests (`/generate`, `/substitute`).
    * Manages user authentication (`/register`, `/login`, `/logout`) and sessions.
    * Interacts with the PostgreSQL database for user credentials.
    * Acts as a client to the Google Gemini API.
    * Handles decoding of stateless share links (`/share`).
* **Database:** PostgreSQL stores user login details (`login_details` table).
* **LLM API:** Google Gemini API (specifically tested with `gemini-1.5-flash-latest`) via REST calls.
* **Persistence:**
    * User Auth: PostgreSQL.
    * Shopping List: Browser LocalStorage.
    * Shared Recipes: Stateless (encoded in URL).

## 💻 Technologies Used

* **Backend:** Python, Flask, Werkzeug
* **Database:** PostgreSQL, psycopg2 (Python adapter)
* **Frontend:** HTML, CSS, JavaScript (ES6+), Bootstrap 5
* **APIs:** Google Gemini Generative Language API
* **Environment:** python-dotenv
* **Libraries:** requests

## 🚀 Setup and Installation

Follow these steps to set up and run the project locally:

1.  **Prerequisites:**
    * Python 3.8+ installed.
    * PostgreSQL server installed and running.
    * Git installed.

2.  **Clone Repository:**
    ```bash
    git clone <your-repository-url>
    cd recipe_app
    ```

3.  **Create Virtual Environment:** (Recommended)
    ```bash
    python -m venv venv
    ```
    Activate it:
    * Windows: `.\venv\Scripts\activate`
    * macOS/Linux: `source venv/bin/activate`

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure your `requirements.txt` file includes Flask, psycopg2-binary, requests, python-dotenv, Werkzeug).*

5.  **Database Setup:**
    * Connect to your PostgreSQL instance (using `psql` or a GUI like pgAdmin).
    * Create the database specified in your `.env` file (default is `expense`):
        ```sql
        CREATE DATABASE expense;
        ```
    * The necessary `login_details` table will be created automatically when the Flask app starts for the first time by the `init_db()` function. Ensure the database user has permission to create tables.

6.  **Environment Variables:**
    * Create a file named `.env` in the root `recipe_app` directory.
    * Add the following variables, replacing placeholder values with your actual credentials and keys:

        ```dotenv
        # .env Example
        FLASK_APP=app.py
        FLASK_ENV=development # Use 'development' for debugging, 'production' for deployment
        FLASK_DEBUG=1         # Explicitly enable debug mode for development (0 for off)

        # Generate a strong secret key (e.g., python -c 'import secrets; print(secrets.token_hex(24))')
        SECRET_KEY='YOUR_VERY_STRONG_RANDOM_SECRET_KEY'

        # Get your API key from Google AI Studio ([https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey))
        GEMINI_API_KEY='YOUR_GOOGLE_GEMINI_API_KEY'

        # Database Credentials
        DB_NAME=expense
        DB_USER=postgres
        DB_PASSWORD=your_db_password # Replace with your actual DB password
        DB_HOST=localhost          # Or your DB host if different
        DB_PORT=5432               # Or your DB port if different
        ```
    * **IMPORTANT:** Never commit your `.env` file to Git. Add `.env` to your `.gitignore` file.

## ▶️ Running the Application

1.  Ensure your virtual environment is activated.
2.  Make sure your PostgreSQL server is running.
3.  Run the Flask development server from the `recipe_app` directory:

    ```bash
    flask run
    ```
    or
    ```bash
    python app.py
    ```
4.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the URL provided in the terminal).

## 🖱️ Usage

1.  **Login/Register:** You can register a new account or log in. Alternatively, click "Skip Login" to proceed directly to recipe generation (sharing might require login depending on final implementation choices, saving to profile definitely would).
2.  **Generate Recipe:** Enter ingredients (one per line or comma-separated), add optional descriptions, dietary filters, or cuisine styles, and click "Generate Recipe".
3.  **View Recipe:** The generated recipe will appear on the right, including title, description, ingredients, steps, and estimated times (if provided by the LLM).
4.  **Actions:**
    * **Find Substitute:** Click the button next to an ingredient to get substitution ideas.
    * **Add to Shopping List:** Adds all ingredients from the current recipe to the shopping list on the left.
    * **Share Recipe:** Opens a modal with a shareable link (which encodes the recipe data) and options to copy or share via Email, Facebook, Twitter, WhatsApp, or the system's native share dialog (if supported). **Note:** Links can be very long.
    * **Save Recipe (.txt):** Downloads the current recipe as a plain text file.
5.  **Shopping List:**
    * Manually add items using the input field.
    * Check items off using the checkboxes.
    * Remove items using the 'x' button.
    * Copy the current list to the clipboard.
    * Clear the entire list.
    * The list is saved automatically in your browser's LocalStorage.

## 💡 Future Enhancements

* **Server-Side Sharing:** Implement Option B (storing shared recipes in the database) to generate much shorter, more user-friendly share URLs.
* **User Profiles:** Allow users to save generated recipes to their account (requires database changes).
* **Recipe History:** Store a history of generated recipes for logged-in users.
* **Improved Substitution:** More context-aware substitutions (e.g., specifying "for baking").
* **Advanced Filtering:** More granular filters (allergens, cooking time limits, skill level).
* **UI/UX Polish:** Improve visual design, add loading indicators for substitutions, use toasts for feedback instead of alerts.
* **Testing:** Add unit and integration tests for backend routes and utilities. Add frontend tests.
* **Deployment:** Configure for deployment using a production WSGI server (like Gunicorn or Waitress) and potentially containerization (Docker).


