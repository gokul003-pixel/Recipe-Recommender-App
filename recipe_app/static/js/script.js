// static/js/script.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Elements ---
    const recipeForm = document.getElementById('recipe-form');
    const recipeOutput = document.getElementById('recipe-output');
    const generateBtn = document.getElementById('generate-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const recipeActions = document.getElementById('recipe-actions');
    const substitutionOutput = document.getElementById('substitution-output');
    // Shopping List Elements
    const shoppingListSection = document.getElementById('shopping-list-section');
    const shoppingListItemsDiv = document.getElementById('shopping-list-items');
    const manualAddItemInput = document.getElementById('manual-add-item');
    const manualAddBtn = document.getElementById('manual-add-btn');
    const addToListBtn = document.getElementById('add-to-list-btn');
    const copyListBtn = document.getElementById('copy-list-btn');
    const clearListBtn = document.getElementById('clear-list-btn');
    const copyListTextarea = document.getElementById('copy-list-textarea');
    // Share Elements
    const shareRecipeBtn = document.getElementById('share-recipe-btn');
    const shareModal = document.getElementById('shareModal');
    const shareUrlInput = document.getElementById('share-url-input');
    const copyShareLinkBtn = document.getElementById('copy-share-link-btn');
    const copyLinkFeedback = document.getElementById('copy-link-feedback');
    const shareEmailLink = document.getElementById('share-email-link');
    const shareFacebookLink = document.getElementById('share-facebook-link');
    const shareTwitterLink = document.getElementById('share-twitter-link');
    const shareWhatsappLink = document.getElementById('share-whatsapp-link'); // Added
    const directShareBtn = document.getElementById('direct-share-btn'); // Added
    // Save Button Element
    const saveRecipeBtn = document.getElementById('save-recipe-btn'); // Added


    // --- State Variables ---
    let currentRecipeData = null; // Store the currently displayed recipe
    let shoppingList = []; // In-memory shopping list
    const SHOPPING_LIST_KEY = 'recipeAppShoppingListData'; // LocalStorage Key

    // --- Helper Functions ---
    function escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return '';
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    function showLoading(isLoading) {
        if (!generateBtn || !loadingIndicator) return;
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

    function sanitizeFilename(name) {
        // Replace spaces with underscores, remove invalid characters
        if (!name || typeof name !== 'string') return 'recipe';
        const sanitized = name.trim()
                           .replace(/\s+/g, '_')
                           .replace(/[<>:"/\\|?*\x00-\x1F]/g, '');
        return sanitized || 'recipe'; // Ensure not empty
     }

    // --- Recipe Generation Logic ---
    if (recipeForm) {
        recipeForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            showLoading(true);
            if (recipeOutput) recipeOutput.innerHTML = '<p>Generating your recipe...</p>';
            if (recipeActions) recipeActions.style.display = 'none';
            if (substitutionOutput) substitutionOutput.innerHTML = '';
            currentRecipeData = null;

            const ingredientsText = document.getElementById('ingredients')?.value || '';
            const description = document.getElementById('description')?.value || '';
            const diet = document.getElementById('diet')?.value || '';
            const cuisine = document.getElementById('cuisine')?.value || '';
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
                    let errorMsg = `HTTP error! Status: ${response.status}`;
                    try { const errorData = await response.json(); errorMsg = errorData.error || `Server error ${response.status}`; } catch (e) {}
                    throw new Error(errorMsg);
                }
                const data = await response.json();
                if (typeof window.displayRecipe === 'function') {
                    window.displayRecipe(data);
                } else {
                     console.error("displayRecipe function is not defined globally.");
                     if(recipeOutput) recipeOutput.innerHTML = '<p class="text-danger">Error: Cannot display recipe result.</p>';
                }
            } catch (error) {
                console.error("Error generating recipe:", error);
                if (recipeOutput) recipeOutput.innerHTML = `<div class="alert alert-danger" role="alert">Failed to generate recipe: ${escapeHtml(error.message)}. Please try again.</div>`;
                currentRecipeData = null;
            } finally {
                 showLoading(false);
            }
        });
    }

    // --- Display Recipe Function ---
    window.displayRecipe = function(recipeData) {
        if (!recipeOutput || !recipeActions) {
             console.error("Recipe output or actions element not found.");
             return;
        }
        if (!recipeData || typeof recipeData !== 'object' || !recipeData.title || !recipeData.ingredients || !Array.isArray(recipeData.ingredients) || !recipeData.steps || !Array.isArray(recipeData.steps)) {
            recipeOutput.innerHTML = `<div class="alert alert-warning" role="alert">Recipe data is incomplete or invalid.</div>`;
            console.warn("Incomplete/invalid recipe data received:", recipeData);
            currentRecipeData = null;
            recipeActions.style.display = 'none';
            return;
        }
        currentRecipeData = recipeData; // Store valid data
        let recipeHtml = `<h3>${escapeHtml(recipeData.title)}</h3>`;
        if (recipeData.description) recipeHtml += `<p><em>${escapeHtml(recipeData.description)}</em></p>`;
        if (recipeData.prep_time || recipeData.cook_time) {
             recipeHtml += `<p class="small text-muted">`;
             if (recipeData.prep_time) recipeHtml += `<strong>Prep:</strong> ${escapeHtml(recipeData.prep_time)} `;
             if (recipeData.cook_time) recipeHtml += `<strong>Cook:</strong> ${escapeHtml(recipeData.cook_time)}`;
             recipeHtml += `</p>`;
        }
         recipeHtml += `<h5>Ingredients:</h5><ul>`;
         recipeData.ingredients.forEach(ing => {
             const ingredientText = (typeof ing === 'string' || typeof ing === 'number') ? String(ing) : 'Invalid ingredient';
             recipeHtml += `<li>${escapeHtml(ingredientText)} <button class="btn btn-sm btn-outline-secondary ms-2 btn-substitute" data-ingredient="${escapeHtml(ingredientText)}">Find Substitute</button></li>`;
         });
         recipeHtml += `</ul>`;
         recipeHtml += `<h5>Steps:</h5><ol>`;
         recipeData.steps.forEach(step => {
            const stepText = (typeof step === 'string' || typeof step === 'number') ? String(step) : 'Invalid step';
             recipeHtml += `<li>${escapeHtml(stepText)}</li>`;
         });
         recipeHtml += `</ol>`;
        recipeOutput.innerHTML = recipeHtml;
        recipeActions.style.display = 'block';
        addSubstituteButtonListeners();
        if(substitutionOutput) substitutionOutput.innerHTML = '';
    }

    // --- Substitute Logic ---
    function addSubstituteButtonListeners() {
         const substituteButtons = recipeOutput?.querySelectorAll('.btn-substitute');
         if (!substituteButtons) return;
         substituteButtons.forEach(button => button.replaceWith(button.cloneNode(true))); // Remove old listeners
         recipeOutput.querySelectorAll('.btn-substitute').forEach(button => button.addEventListener('click', handleSubstituteClick)); // Add new
     }
    async function handleSubstituteClick() { /* ... same implementation as before ... */ }


    // --- Shopping List Logic ---
    function loadShoppingList() { /* ... same implementation as before ... */ }
    function saveShoppingList() { /* ... same implementation as before ... */ }
    function categorizeIngredient(name) { /* ... same implementation as before ... */ }
    function renderShoppingList() { /* ... same implementation as before ... */ }
    function addShoppingListItem(itemName) { /* ... same implementation as before ... */ }
    if (addToListBtn) { /* ... same listener as before ... */ }
    if (manualAddBtn && manualAddItemInput) { /* ... same listener as before ... */ }
    if (shoppingListItemsDiv) { /* ... same listener as before ... */ }
    if (copyListBtn) { /* ... same listener as before ... */ }
    if (clearListBtn) { /* ... same listener as before ... */ }


    // --- Recipe Sharing Logic (Stateless) ---
    function encodeRecipeData(recipeData) {
        try {
            const jsonString = JSON.stringify(recipeData);
            const base64 = btoa(unescape(encodeURIComponent(jsonString)));
            return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
        } catch (e) {
            console.error("Error encoding recipe data:", e); return null;
        }
    }

    if (shareModal) {
         shareModal.addEventListener('show.bs.modal', function (event) {
            if (!currentRecipeData) {
                alert("No recipe data available to share."); event.preventDefault(); return;
            }
            const encodedData = encodeRecipeData(currentRecipeData);
            if (!encodedData) {
                alert("Could not generate sharing link."); event.preventDefault(); return;
            }
            const shareUrl = `${window.location.origin}/share?data=${encodedData}`;
            const recipeTitle = currentRecipeData.title || "Recipe";
            const shareText = `Check out this recipe: ${recipeTitle}`;

            if(shareUrlInput) shareUrlInput.value = shareUrl;
            if(shareEmailLink) shareEmailLink.href = `mailto:?subject=${encodeURIComponent(shareText)}&body=${encodeURIComponent('Recipe Link: ' + shareUrl)}`;
            if(shareFacebookLink) shareFacebookLink.href = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`;
            if(shareTwitterLink) shareTwitterLink.href = `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`;
            // Setup WhatsApp Link
            if(shareWhatsappLink) shareWhatsappLink.href = `https://wa.me/?text=${encodeURIComponent(shareText + ' - ' + shareUrl)}`;

            // Setup Direct Share Button
             if (directShareBtn) {
                 if (navigator.share) {
                     directShareBtn.style.display = 'inline-block';
                     // Detach previous listener if any to prevent duplicates
                     const newDirectShareBtn = directShareBtn.cloneNode(true);
                     directShareBtn.parentNode.replaceChild(newDirectShareBtn, directShareBtn);
                     // Add listener to the new button
                     newDirectShareBtn.addEventListener('click', async () => {
                         try {
                             await navigator.share({ title: recipeTitle, text: shareText, url: shareUrl });
                             console.log('Recipe shared successfully via Web Share API');
                         } catch (err) {
                             console.error('Error using Web Share API:', err);
                         }
                     });
                 } else {
                     directShareBtn.style.display = 'none';
                 }
             }
            if(copyLinkFeedback) copyLinkFeedback.style.display = 'none';
            if(copyShareLinkBtn) copyShareLinkBtn.disabled = false;
         });
    }

    if (copyShareLinkBtn && shareUrlInput) { /* ... same listener as before ... */ }


    // --- Save Recipe Logic ---
    if (saveRecipeBtn) {
        saveRecipeBtn.addEventListener('click', function() {
            if (!currentRecipeData) {
                alert("No recipe data available to save."); return;
            }
            let recipeText = "";
            const title = currentRecipeData.title || "Untitled Recipe";
            recipeText += title + "\n" + "=".repeat(title.length) + "\n\n";
            if (currentRecipeData.description) recipeText += "Description:\n" + currentRecipeData.description + "\n\n";
            if (currentRecipeData.prep_time) recipeText += "Prep Time: " + currentRecipeData.prep_time + "\n";
            if (currentRecipeData.cook_time) recipeText += "Cook Time: " + currentRecipeData.cook_time + "\n";
            if (currentRecipeData.prep_time || currentRecipeData.cook_time) recipeText += "\n";
            if (currentRecipeData.ingredients && currentRecipeData.ingredients.length > 0) {
                recipeText += "Ingredients:\n";
                currentRecipeData.ingredients.forEach(ing => { recipeText += "- " + ((typeof ing === 'string' || typeof ing === 'number') ? String(ing) : '?') + "\n"; });
                recipeText += "\n";
            }
            if (currentRecipeData.steps && currentRecipeData.steps.length > 0) {
                recipeText += "Steps:\n";
                currentRecipeData.steps.forEach((step, index) => { recipeText += (index + 1) + ". " + ((typeof step === 'string' || typeof step === 'number') ? String(step) : '?') + "\n"; });
                recipeText += "\n";
            }
            const blob = new Blob([recipeText], { type: 'text/plain;charset=utf-8' });
            const link = document.createElement("a");
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            const filename = sanitizeFilename(title) + ".txt";
            link.setAttribute("download", filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            console.log(`Recipe saved as ${filename}`);
        });
    }

    // --- Initial Load ---
    loadShoppingList(); // Load shopping list when DOM is ready

}); // End DOMContentLoaded