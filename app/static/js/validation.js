// Remove red border and hide error message when user inputs on invalid field
document.querySelectorAll("input").forEach(input => {

    input.addEventListener("input", () => {

        input.classList.remove("is-invalid");
        const error = input.parentElement.querySelector(".invalid-feedback");

        if (error) {
            error.classList.add("d-none");
        }

    });
});