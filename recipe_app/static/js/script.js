// static/js/script.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Existing Elements ---
    const recipeForm = document.getElementById('recipe-form');
    const recipeOutput = document.getElementById('recipe-output');
    const generateBtn = document.getElementById('generate-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const recipeActions = document.getElementById('recipe-actions');
    const substitutionOutput = document.getElementById('substitution-output');

    // --- NEW: Shopping List Elements ---
    const shoppingListSection = document.getElementById('shopping-list-section');
    const shoppingListItemsDiv = document.getElementById('shopping-list-items');
    const manualAddItemInput = document.getElementById('manual-add-item');
    const manualAddBtn = document.getElementById('manual-add-btn');
    const addToListBtn = document.getElementById('add-to-list-btn'); // Button by the recipe
    const copyListBtn = document.getElementById('copy-list-btn');
    const clearListBtn = document.getElementById('clear-list-btn');
    const copyListTextarea = document.getElementById('copy-list-textarea'); // Hidden textarea

    // --- State Variables ---
    let currentRecipeData = null; // Store the currently displayed recipe
    let shoppingList = []; // In-memory shopping list
    const SHOPPING_LIST_KEY = 'recipeAppShoppingListData'; // LocalStorage Key

    // --- Function to escape HTML ---
    function escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return '';
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    // --- Function to Show/Hide Loading ---
    function showLoading(isLoading) {
        if (isLoading) {
            loadingIndicator.style.display = 'inline-block';
            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating...';
        } else {
            loadingIndicator.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Recipe';
        }
    }

    // --- Recipe Generation Logic (Existing, slightly modified) ---
    if (recipeForm) {
        recipeForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            showLoading(true);
            recipeOutput.innerHTML = '<p>Generating your recipe...</p>';
            recipeActions.style.display = 'none';
            substitutionOutput.innerHTML = '';
            currentRecipeData = null; // Clear previous recipe data

            const ingredientsText = document.getElementById('ingredients').value;
            const description = document.getElementById('description').value;
            const diet = document.getElementById('diet').value;
            const cuisine = document.getElementById('cuisine').value;
            const ingredients = ingredientsText.split(/[\n,]+/).map(item => item.trim()).filter(item => item.length > 0);
            const filters = {};
            if (diet) filters.diet = diet;
            if (cuisine) filters.cuisine = cuisine;
            const payload = { ingredients, description, filters };

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!response.ok) {
                    let errorMsg = `HTTP error! status: ${response.status}`;
                    try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) {}
                    throw new Error(errorMsg);
                }
                const data = await response.json();
                displayRecipe(data); // Call display function

            } catch (error) {
                console.error("Error generating recipe:", error);
                recipeOutput.innerHTML = `<div class="alert alert-danger" role="alert">Failed to generate recipe. ${error.message}. Please try again.</div>`;
                currentRecipeData = null; // Ensure no stale data
            } finally {
                 showLoading(false);
            }
        });
    }

    // --- Display Recipe Function (Existing, slightly modified) ---
    // Make it globally accessible for shared links and store current recipe
    window.displayRecipe = function(recipeData) {
        if (!recipeData || typeof recipeData !== 'object') {
            recipeOutput.innerHTML = `<div class="alert alert-warning" role="alert">Received invalid recipe data format.</div>`;
            currentRecipeData = null;
            return;
        }
        if (!recipeData.title || !recipeData.ingredients || !recipeData.steps) {
            recipeOutput.innerHTML = `<div class="alert alert-warning" role="alert">Recipe data is missing essential fields (title, ingredients, or steps).</div>`;
            // Attempt to display partial data (optional)
            currentRecipeData = null;
            recipeActions.style.display = 'none';
            return;
        }

        // Store the valid recipe data
        currentRecipeData = recipeData;

        // Build HTML for the recipe
        let recipeHtml = `<h3>${escapeHtml(recipeData.title)}</h3>`;
        if (recipeData.description) {
             recipeHtml += `<p><em>${escapeHtml(recipeData.description)}</em></p>`;
        }
        if (recipeData.prep_time || recipeData.cook_time) {
             recipeHtml += `<p>`;
             if (recipeData.prep_time) recipeHtml += `<strong>Prep:</strong> ${escapeHtml(recipeData.prep_time)} `;
             if (recipeData.cook_time) recipeHtml += `<strong>Cook:</strong> ${escapeHtml(recipeData.cook_time)}`;
             recipeHtml += `</p>`;
        }

         recipeHtml += `<h5>Ingredients:</h5><ul>`;
         recipeData.ingredients.forEach(ingredient => {
             recipeHtml += `<li>${escapeHtml(ingredient)}
                             <button class="btn btn-sm btn-outline-secondary ms-2 btn-substitute" data-ingredient="${escapeHtml(ingredient)}">Find Substitute</button>
                           </li>`;
         });
         recipeHtml += `</ul>`;

         recipeHtml += `<h5>Steps:</h5><ol>`;
         recipeData.steps.forEach(step => {
             recipeHtml += `<li>${escapeHtml(step)}</li>`;
         });
         recipeHtml += `</ol>`;

        // Display the HTML
        recipeOutput.innerHTML = recipeHtml;
        recipeActions.style.display = 'block'; // Show action buttons including "Add to List"
        addSubstituteButtonListeners(); // Re-attach listeners for substitute buttons
    }

    // --- Substitute Logic (Existing - Placeholder for brevity, use your actual logic) ---
    function addSubstituteButtonListeners() {
         const substituteButtons = recipeOutput.querySelectorAll('.btn-substitute');
         substituteButtons.forEach(button => {
             button.addEventListener('click', async function() {
                 const ingredient = this.dataset.ingredient;
                 if (!ingredient) return;
                 this.disabled = true;
                 this.textContent = 'Finding...';
                 substitutionOutput.innerHTML = `<p>Looking for substitutes for <strong>${escapeHtml(ingredient)}</strong>...</p>`;
                 try {
                     const response = await fetch('/substitute', {
                         method: 'POST',
                         headers: { 'Content-Type': 'application/json' },
                         body: JSON.stringify({ ingredient: ingredient })
                     });
                     if (!response.ok) throw new Error(`Network response was not ok (${response.status})`);
                     const data = await response.json();
                     if (data.substitutions && data.substitutions.length > 0) {
                         let subHtml = `<p>Substitutes for <strong>${escapeHtml(ingredient)}</strong>:</p><ul>`;
                         data.substitutions.forEach(sub => { subHtml += `<li>${escapeHtml(sub)}</li>`; });
                         subHtml += `</ul>`;
                         substitutionOutput.innerHTML = subHtml;
                     } else {
                          substitutionOutput.innerHTML = `<p>No substitution suggestions found for <strong>${escapeHtml(ingredient)}</strong>.</p>`;
                     }
                 } catch (error) {
                      console.error("Error fetching substitutions:", error);
                      substitutionOutput.innerHTML = `<p class="text-danger">Could not fetch substitutions for <strong>${escapeHtml(ingredient)}</strong>. Error: ${error.message}</p>`;
                 } finally {
                      this.disabled = false;
                      this.textContent = 'Find Substitute';
                 }
             });
         });
     }

    // ======================================= //
    // === NEW: SHOPPING LIST LOGIC BELOW ==== //
    // ======================================= //

    // --- Shopping List: Load from LocalStorage ---
    function loadShoppingList() {
        const storedList = localStorage.getItem(SHOPPING_LIST_KEY);
        if (storedList) {
            try {
                shoppingList = JSON.parse(storedList);
                if (!Array.isArray(shoppingList)) { // Basic validation
                    console.warn("Stored shopping list is not an array, resetting.");
                    shoppingList = [];
                }
                // Ensure items have necessary properties (migration if needed)
                shoppingList = shoppingList.map(item => ({
                     id: item.id || crypto.randomUUID(), // Assign ID if missing
                     name: item.name || "Unknown Item",
                     category: item.category || categorizeIngredient(item.name || ""),
                     checked: item.checked || false
                 }));
            } catch (e) {
                console.error("Error parsing shopping list from localStorage:", e);
                shoppingList = []; // Reset if parsing fails
            }
        } else {
            shoppingList = []; // Initialize if nothing is stored
        }
        renderShoppingList(); // Render the loaded/initialized list
    }

    // --- Shopping List: Save to LocalStorage ---
    function saveShoppingList() {
        try {
            localStorage.setItem(SHOPPING_LIST_KEY, JSON.stringify(shoppingList));
        } catch (e) {
            console.error("Error saving shopping list to localStorage:", e);
            // Handle potential storage quota errors
            alert("Could not save shopping list, browser storage might be full.");
        }
    }

    // --- Shopping List: Categorize Ingredient (Simple Heuristics) ---
    function categorizeIngredient(name) {
        if (!name) return "Miscellaneous";
        const lowerName = name.toLowerCase();
        // Prioritize specific keywords
        if (/\b(salt|pepper|cumin|paprika|turmeric|oregano|basil|parsley|spice|herb|cinnamon|ginger|garlic powder|onion powder)\b/.test(lowerName)) return "Spices & Herbs";
        if (/\b(oil|butter|margarine|lard|ghee|shortening|spray)\b/.test(lowerName)) return "Oils & Fats";
        if (/\b(flour|sugar|baking soda|baking powder|yeast|cocoa|vanilla|chocolate chip|sweetener|extract)\b/.test(lowerName)) return "Baking";
        if (/\b(milk|cream|cheese|yogurt|sour cream|egg|butter)\b/.test(lowerName) && !/\b(coconut|oat|almond|soy)\b/.test(lowerName)) return "Dairy & Eggs"; // Avoid plant milks here
        if (/\b(coconut milk|oat milk|almond milk|soy milk|cashew cream)\b/.test(lowerName)) return "Plant-Based Milks/Creams";
        if (/\b(chicken|beef|pork|lamb|turkey|fish|salmon|tuna|shrimp|seafood|meat|bacon|sausage)\b/.test(lowerName)) return "Meat & Seafood";
        if (/\b(tofu|tempeh|seitan|edamame)\b/.test(lowerName)) return "Plant-Based Protein";
        if (/\b(onion|garlic|carrot|potato|tomato|broccoli|spinach|lettuce|pepper|celery|cucumber|mushroom|greens|vegetable|corn|pea)\b/.test(lowerName)) return "Vegetables";
        if (/\b(apple|banana|orange|berry|berries|strawberry|blueberry|lemon|lime|fruit|grape|melon|avocado)\b/.test(lowerName)) return "Fruits";
        if (/\b(rice|pasta|bread|noodle|quinoa|oat|cereal|grain|couscous|tortilla|cracker|bun)\b/.test(lowerName)) return "Grains & Pasta";
        if (/\b(bean|lentil|chickpea|legume)\b/.test(lowerName)) return "Legumes";
        if (/\b(soy sauce|vinegar|ketchup|mustard|mayo|hot sauce|broth|stock|paste|canned|jar|sauce|condiment|bouillon)\b/.test(lowerName)) return "Pantry/Canned Goods";
        if (/\b(water|juice|soda|wine|beer|beverage|drink)\b/.test(lowerName)) return "Beverages";
        if (/\b(nut|seed|almond|peanut|cashew|walnut|chia|flax)\b/.test(lowerName)) return "Nuts & Seeds";

        return "Miscellaneous"; // Default category
    }

    // --- Shopping List: Render the List to HTML ---
    function renderShoppingList() {
        if (!shoppingListItemsDiv) return;

        if (shoppingList.length === 0) {
            shoppingListItemsDiv.innerHTML = '<p><em>Your shopping list is empty.</em></p>';
            // Disable action buttons when list is empty
            if(copyListBtn) copyListBtn.disabled = true;
            if(clearListBtn) clearListBtn.disabled = true;
            return;
        }
        // Enable action buttons when list has items
        if(copyListBtn) copyListBtn.disabled = false;
        if(clearListBtn) clearListBtn.disabled = false;


        // Group items by category
        const groupedList = shoppingList.reduce((acc, item) => {
            const category = item.category || "Miscellaneous"; // Fallback category
            if (!acc[category]) {
                acc[category] = [];
            }
            acc[category].push(item);
            return acc;
        }, {});

        // Sort categories alphabetically
        const sortedCategories = Object.keys(groupedList).sort();

        let listHtml = '';
        sortedCategories.forEach(category => {
            // Sort items within category alphabetically (optional)
            const sortedItems = groupedList[category].sort((a, b) => a.name.localeCompare(b.name));

            listHtml += `<h5 class="mt-3 text-primary">${escapeHtml(category)}</h5>`; // Category header
            listHtml += `<ul class="list-group list-group-flush mb-2">`; // Use Bootstrap list group
            sortedItems.forEach(item => {
                const isChecked = item.checked || false;
                const textDecoration = isChecked ? 'text-decoration-line-through text-muted' : '';
                const uniqueId = `item-${item.id}`; // Create unique ID for label association
                listHtml += `
                    <li class="list-group-item d-flex justify-content-between align-items-center ps-2 ${isChecked ? 'list-group-item-light' : ''}">
                        <div class="form-check flex-grow-1 me-2">
                           <input class="form-check-input shopping-item-check" type="checkbox" value="" id="${uniqueId}" data-id="${item.id}" ${isChecked ? 'checked' : ''} title="Check/uncheck item">
                           <label class="form-check-label ${textDecoration}" for="${uniqueId}">
                                ${escapeHtml(item.name)}
                           </label>
                        </div>
                        <button class="btn btn-sm btn-outline-danger btn-delete-item py-0 px-1" data-id="${item.id}" aria-label="Remove item" title="Remove item">&times;</button>
                    </li>
                `;
            });
            listHtml += `</ul>`;
        });

        shoppingListItemsDiv.innerHTML = listHtml;
    }

    // --- Shopping List: Add Item (used by manual add and recipe add) ---
    function addShoppingListItem(itemName) {
        if (!itemName || typeof itemName !== 'string' || !itemName.trim()) {
            return false; // Indicate failure: Don't add empty items
        }
        const trimmedName = itemName.trim();

        // Basic check for duplicates (case-insensitive)
        const exists = shoppingList.some(item => item.name.toLowerCase() === trimmedName.toLowerCase());
        if (exists) {
            console.log(`Item "${trimmedName}" already in list.`);
            // Optionally flash a message or highlight existing item
            // Find the existing item and scroll to it maybe?
            return false; // Indicate failure: duplicate
        }

        const newItem = {
            id: crypto.randomUUID(), // Generate unique ID
            name: trimmedName,
            category: categorizeIngredient(trimmedName),
            checked: false
        };
        shoppingList.push(newItem); // Add to in-memory list
        return true; // Indicate success
    }


    // --- Shopping List: Handle Add from Recipe Button ---
    if (addToListBtn) {
        addToListBtn.addEventListener('click', function() {
            if (!currentRecipeData || !currentRecipeData.ingredients || currentRecipeData.ingredients.length === 0) {
                alert("No recipe ingredients found to add.");
                return;
            }

            let addedCount = 0;
            currentRecipeData.ingredients.forEach(ingredient => {
                // Use the common add function which handles trimming and basic duplicate check
                if (addShoppingListItem(ingredient)) {
                    addedCount++;
                }
            });

            if (addedCount > 0) {
                saveShoppingList(); // Save once after adding all items
                renderShoppingList();
                alert(`${addedCount} new item(s) added to the shopping list.`);
            } else {
                 alert("All ingredients from this recipe are already in your shopping list or are empty.");
            }
        });
    }

    // --- Shopping List: Handle Manual Add ---
    if (manualAddBtn && manualAddItemInput) {
        manualAddBtn.addEventListener('click', function() {
            const itemName = manualAddItemInput.value;
            if (addShoppingListItem(itemName)) { // If adding was successful (not duplicate/empty)
                saveShoppingList();
                renderShoppingList();
                manualAddItemInput.value = ''; // Clear input field only on success
            } else if (itemName.trim()) { // If not successful, but input wasn't empty (i.e., it was a duplicate)
                 alert(`"${itemName.trim()}" is already on the list.`);
            }
            manualAddItemInput.focus(); // Keep focus on input
        });

        // Add item on Enter key press
        manualAddItemInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent potential form submission
                manualAddBtn.click(); // Trigger the button click
            }
        });
    }

    // --- Shopping List: Handle Checkbox Changes and Deletions (Event Delegation) ---
    if (shoppingListItemsDiv) {
        shoppingListItemsDiv.addEventListener('click', function(event) {
            const target = event.target;

            // Handle Checkbox Click
            if (target.matches('.shopping-item-check')) {
                const itemId = target.dataset.id;
                const itemIndex = shoppingList.findIndex(item => item.id === itemId);
                if (itemIndex > -1) {
                    shoppingList[itemIndex].checked = target.checked; // Update checked state
                    saveShoppingList();
                    // Could just update the style of the parent LI and label instead of full re-render
                    const listItem = target.closest('li');
                    const label = listItem.querySelector('label');
                    if (target.checked) {
                        listItem.classList.add('list-group-item-light');
                        label.classList.add('text-decoration-line-through', 'text-muted');
                    } else {
                        listItem.classList.remove('list-group-item-light');
                        label.classList.remove('text-decoration-line-through', 'text-muted');
                    }
                    // renderShoppingList(); // Full re-render is simpler for now
                }
            }

            // Handle Delete Button Click
            if (target.matches('.btn-delete-item')) {
                const itemId = target.dataset.id;
                const itemIndex = shoppingList.findIndex(item => item.id === itemId);
                if (itemIndex > -1) {
                    // Optional: Confirm deletion
                    // if (!confirm(`Remove "${shoppingList[itemIndex].name}" from the list?`)) {
                    //     return;
                    // }
                    shoppingList.splice(itemIndex, 1); // Remove item using splice
                    saveShoppingList();
                    renderShoppingList(); // Re-render the list
                }
            }
        });
    }

    // --- Shopping List: Handle Copy Button ---
    if (copyListBtn) {
        copyListBtn.addEventListener('click', async function() {
            if (shoppingList.length === 0) {
                alert("Shopping list is empty. Nothing to copy.");
                return;
            }

            // Sort list by category, then name for consistent copying
            const sortedListForCopy = [...shoppingList].sort((a,b) => {
                if (a.category < b.category) return -1;
                if (a.category > b.category) return 1;
                return a.name.localeCompare(b.name); // Sort by name within category
            });


            let textToCopy = "Shopping List\n=============\n\n";
            let currentCategory = null;

            sortedListForCopy.forEach(item => {
                 const category = item.category || "Miscellaneous";
                 if (category !== currentCategory) {
                    if (currentCategory !== null) textToCopy += "\n"; // Add space before new category
                    textToCopy += `--- ${category} ---\n`;
                    currentCategory = category;
                 }
                 textToCopy += `[${item.checked ? 'x' : ' '}] ${item.name}\n`;
             });

            // Use Clipboard API
            try {
                 await navigator.clipboard.writeText(textToCopy);
                 // Provide visual feedback instead of alert (optional)
                 const originalText = copyListBtn.textContent;
                 copyListBtn.textContent = 'Copied!';
                 copyListBtn.classList.remove('btn-info');
                 copyListBtn.classList.add('btn-success');
                 setTimeout(() => {
                    copyListBtn.textContent = originalText;
                    copyListBtn.classList.remove('btn-success');
                    copyListBtn.classList.add('btn-info');
                 }, 2000); // Revert after 2 seconds

            } catch (err) {
                 console.error('Failed to copy text using Clipboard API: ', err);
                 // Fallback attempt (less reliable)
                 try {
                     copyListTextarea.value = textToCopy;
                     copyListTextarea.style.display = 'block'; // Temporarily show for selection
                     copyListTextarea.select();
                     copyListTextarea.setSelectionRange(0, 99999); // For mobile devices
                     document.execCommand('copy');
                     copyListTextarea.style.display = 'none'; // Hide again
                     alert("Shopping list copied to clipboard! (Fallback method)");
                 } catch (fallbackErr) {
                     console.error('Fallback copy method failed:', fallbackErr);
                     copyListTextarea.style.display = 'none';
                     alert("Could not copy list automatically. Please try again or copy manually.");
                 }
            }
        });
    }

    // --- Shopping List: Handle Clear Button ---
    if (clearListBtn) {
        clearListBtn.addEventListener('click', function() {
            if (shoppingList.length === 0) {
                // alert("Shopping list is already empty."); // Optional feedback
                return;
            }
            // Confirm before clearing
            if (confirm("Are you sure you want to clear the entire shopping list? This cannot be undone.")) {
                shoppingList = []; // Clear in-memory list
                saveShoppingList(); // Clear localStorage
                renderShoppingList(); // Update UI
            }
        });
    }

    // --- Initial Load ---
    loadShoppingList();

}); // End DOMContentLoaded