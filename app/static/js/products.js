// Price filter validation
const forms = document.querySelectorAll('.filters-form');

forms.forEach(form => {

    const minInput = form.querySelector('input[name="min_price"]');
    const maxInput = form.querySelector('input[name="max_price"]');
    const errorDiv = form.querySelector('.priceError');
    const applyButton = form.querySelector('button[type="submit"]')

    function validatePrice() {
        const min = parseFloat(minInput.value);
        const max = parseFloat(maxInput.value);

        if (!isNaN(min) & !isNaN(max) && min > max) {
            errorDiv.textContent = "Invalid interval";
            applyButton.disabled = true; // Disable submit
        } else {
            errorDiv.textContent = "";
            applyButton.disabled = false; // Enable submit
        }
    }

    // Listen to input changes
    if (minInput && maxInput && errorDiv && applyButton) {
        minInput.addEventListener('input', validatePrice);
        maxInput.addEventListener('input', validatePrice);
        validatePrice();
    }
});