# utils.py
import re
import requests
import json
import os

# --- Gemini LLM Interaction ---

def format_gemini_prompt(ingredients, filters, description):
    """Formats the prompt for the Gemini API for recipe generation."""
    prompt_parts = []
    if description:
        prompt_parts.append(f"{description}.") # Start with general description

    if ingredients:
        prompt_parts.append(f"Generate a recipe primarily using the following ingredients: {', '.join(ingredients)}.")
    else:
        prompt_parts.append("Generate a simple recipe.") # Fallback if no ingredients

    # Add filters (example: dietary, cuisine)
    if filters:
        filter_str = ", ".join([f"{k}: {v}" for k, v in filters.items() if v])
        if filter_str:
             prompt_parts.append(f"Consider these preferences: {filter_str}.")

    # Ask for specific JSON structure for recipes
    prompt_parts.append("Please provide the recipe ONLY in JSON format with keys: 'title' (string), 'description' (string, optional), 'ingredients' (list of strings), 'steps' (list of strings), 'prep_time' (string, e.g., '15 minutes'), 'cook_time' (string, e.g., '30 minutes').")

    return " ".join(prompt_parts)

def call_gemini_api(prompt):
    """
    Calls the Google Gemini API expecting JSON output and returns the
    parsed JSON object or None on failure.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        return None

    # Using v1beta as shown in the original example. Use v1 if available/preferred.
    # Ensure you use a model that supports JSON output mode well, like gemini-1.5-flash-latest
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"

    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json", # Request JSON output directly
        }
        # Add safety settings if needed:
        # "safetySettings": [
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        # ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60) # Use timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        response_json = response.json()

        # Check for prompt feedback which might indicate blocking even with 200 OK
        if 'promptFeedback' in response_json and 'blockReason' in response_json['promptFeedback']:
             print(f"Warning: Prompt potentially blocked. Reason: {response_json['promptFeedback']['blockReason']}")
             # Optionally return None or specific error indicator here if needed

        # Navigate the response structure
        if 'candidates' in response_json and len(response_json['candidates']) > 0:
            content = response_json['candidates'][0].get('content', {})
            if 'parts' in content and len(content['parts']) > 0:
                # Assuming the first part contains the JSON text
                json_text = content['parts'][0].get('text', '{}')
                try:
                    # Parse the JSON string returned by the LLM
                    parsed_data = json.loads(json_text)
                    # Return the parsed data; validation happens in the calling function
                    return parsed_data
                except json.JSONDecodeError:
                    print("Error: Failed to decode JSON from LLM response.")
                    print("Received Text:", json_text)
                    return None
                except Exception as e: # Catch other potential errors during parsing
                    print(f"Error processing LLM JSON response: {e}")
                    print("Received Text:", json_text)
                    return None
            else:
                print("Error: 'parts' not found in LLM response candidate content.")
                print("Received JSON:", response_json)
                return None
        else:
            # Log cases where candidates might be empty due to safety or other reasons
            print("Error: No valid 'candidates' found in LLM response.")
            if 'promptFeedback' in response_json:
                 print("Prompt Feedback:", response_json['promptFeedback'])
            else:
                print("Received JSON:", response_json) # Print full response if no candidates
            return None

    except requests.exceptions.Timeout:
        print("Error: API request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during the API call process
        print(f"An unexpected error occurred during API call: {e}")
        return None


def mock_recipe(ingredients):
    """Fallback mock recipe generator."""
    ing_list = ingredients if ingredients else ["basic items"]
    return {
        "title": "Simple Mock Recipe",
        "description": "A fallback recipe when the AI is unavailable or fails.",
        "ingredients": [f"1 unit of {ing}" for ing in ing_list] + ["1 tbsp olive oil", "Salt and pepper to taste"],
        "steps": [
            f"Prepare {', '.join(ing_list)}.",
            "Heat olive oil in a pan.",
            f"Add {', '.join(ing_list)} and cook until done.",
            "Season with salt and pepper."
        ],
        "prep_time": "5 minutes",
        "cook_time": "10 minutes"
    }

# --- Input Validation ---
def validate_email(email):
    """Basic email format validation."""
    if not email: return False
    # Simple regex, consider using a library like 'email_validator' for robust validation
    if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return True
    return False

def validate_password(password):
    """Password complexity check."""
    if not password: return False, "Password cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
         return False, "Password must contain at least one special character."
    # Add more rules if needed (e.g., uppercase, lowercase)
    # if not re.search(r"[A-Z]", password):
    #     return False, "Password must contain at least one uppercase letter."
    # if not re.search(r"[a-z]", password):
    #     return False, "Password must contain at least one lowercase letter."
    return True, ""

# --- Ingredient Substitution (Updated Logic) ---
STATIC_SUBSTITUTIONS = {
    # Keep this empty or add very reliable, universal substitutions if desired
    # "milk": ["oat milk", "soy milk", "almond milk", "coconut milk (for richness)"],
}

def get_substitutions(ingredient):
    """Provides substitution suggestions using LLM."""
    if not ingredient or not isinstance(ingredient, str):
        return ["Invalid ingredient provided."]

    ingredient_lower = ingredient.lower().strip()

    # 1. Check static map (Optional)
    # if ingredient_lower in STATIC_SUBSTITUTIONS:
    #    print(f"Using static substitution for {ingredient}")
    #    return STATIC_SUBSTITUTIONS[ingredient_lower]

    # 2. LLM Query
    print(f"Querying LLM for substitutes for: {ingredient}")
    # Explicitly ask for the desired JSON format for substitutions
    sub_prompt = (
        f"Suggest 1 to 3 common culinary substitutes for the ingredient: '{ingredient}'. "
        "Consider variations if applicable (e.g., for baking vs savory). "
        "Return the answer ONLY as a valid JSON object with a single key 'substitutes' "
        "whose value is a list of strings (the names of the substitutes). Example: "
        '{"substitutes": ["substitute one", "substitute two"]}'
    )

    # Call the modified API function
    sub_response_data = call_gemini_api(sub_prompt)

    # Validate the *specific* structure needed for substitutions
    if (sub_response_data
            and isinstance(sub_response_data, dict)
            and 'substitutes' in sub_response_data
            and isinstance(sub_response_data['substitutes'], list)):

        # Filter results to ensure they are non-empty strings
        suggestions = [
            s.strip() for s in sub_response_data['substitutes']
            if isinstance(s, str) and s.strip()
        ]

        if suggestions:
             print(f"LLM Suggestions for {ingredient}: {suggestions}")
             return suggestions
        else:
             # Case where LLM returns {"substitutes": []} or {"substitutes": [""]}
             print(f"LLM returned empty suggestions list for {ingredient}.")
             return ["No specific suggestions found."]
    else:
        # Case where LLM failed or returned improperly formatted JSON
        print(f"LLM call failed or gave unexpected JSON format for {ingredient} substitution.")
        print(f"Received data: {sub_response_data}") # Log what was received
        return ["LLM suggestion could not be processed."]