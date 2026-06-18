// Password visibility toggle
document.querySelectorAll('.toggle-password').forEach(button => {
    
    button.addEventListener('click', () => {

        // Get the target input
        const input = document.getElementById(button.dataset.target);

        if (!input) return;

        // Check current input type
        const isPassword = input.type === 'password';

        // Toggle type
        input.type = isPassword ? 'text' : 'password';

        // Update label
        button.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");

        // Get button icon
        const icon = button.querySelector('i');

        // Toggle icons
        if (isPassword) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    });
});

// Check password strength
document.querySelectorAll("form").forEach(form => {

    const passwordInput = form.querySelector(".password-input");
    const passwordHelp = form.querySelector(".password-help");

    if (!passwordInput || !passwordHelp) return;

    passwordInput.addEventListener("focus", () => {
        passwordHelp.classList.remove("d-none");
    });

    passwordInput.addEventListener("input", () => {

        const value = passwordInput.value;

        form.querySelector(".length").style.color = 
            value.length >= 8 ? "green" : "red";

        form.querySelector(".letter").style.color =
            /[A-Za-z]/.test(value) ? "green" : "red";

        form.querySelector(".number").style.color =
            /\d/.test(value) ? "green" : "red";

        form.querySelector(".special").style.color =
            /[@$!%*?&]/.test(value) ? "green" : "red";
    });

});