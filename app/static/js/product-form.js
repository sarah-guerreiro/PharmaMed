// Display subcategories according to selected category
const categorySelect = document.getElementById("category-select");
const subcategorySelect = document.getElementById("subcategory-select");
const subcategoryOptions = subcategorySelect.querySelectorAll("option");
const inventoryMode = subcategorySelect.dataset.inventoryMode === "true";

function updateSubcategories() {

    const selectedCategory = categorySelect.value;

    // Enable subcategory select only outside inventory mode
    if (!inventoryMode) {
        subcategorySelect.disabled = false;
    }

    subcategoryOptions.forEach(option => {

        // Keep placeholder visible
        if (option.value === "") {
            option.hidden = false;
            return;
        }

        // Show matching subcategories
        if (
            option.dataset.parent === selectedCategory
        ) {
            option.hidden = false;
        }

        // Hide others
        else {
            option.hidden = true;
        }
    });
}

// Run when category changes
categorySelect.addEventListener("change", updateSubcategories);

// Run on page load if category already selected
if (categorySelect.value) {
    updateSubcategories();
}

// Display image preview
const imageInput = document.getElementById("image-input");
const imagePreview = document.getElementById("image-preview");
const previewContainer = document.querySelector(".image-preview-container");

imageInput.addEventListener("change", function () {

    const file = this.files[0];

    if (file) {
        const reader = new FileReader();

        reader.addEventListener("load", function () {
            imagePreview.src = reader.result;
            previewContainer.classList.remove("d-none");
        });

        reader.readAsDataURL(file);
    }
});