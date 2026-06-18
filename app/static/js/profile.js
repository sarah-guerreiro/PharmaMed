const firstName = document.querySelector('input[name="first_name"]');
const lastName = document.querySelector('input[name="last_name"]');
const saveChangesBtn = document.getElementById('saveChangesBtn');

// Store original values
const originalFirst = firstName.value;
const originalLast = lastName.value;

// Enable "save changes" button if first or last name change
function checkChanges() {
    if (
        firstName.value !== originalFirst ||
        lastName.value !== originalLast
    ) {
        saveChangesBtn.disabled = false;
    } else {
        saveChangesBtn.disabled = true;
    }
}

// Listen to input changes
firstName.addEventListener("input", checkChanges);
lastName.addEventListener("input", checkChanges);

// Display address form when "add address" button is clicked
document.getElementById("addAddressBtn").addEventListener("click", function() {
    document.getElementById("addressForm").classList.toggle("d-none");
});

// Display edit address form when "edit" button is clicked
document.querySelectorAll(".edit-btn").forEach(button => {
    button.addEventListener("click", function () {
        const id = this.dataset.id;

        const card = document.getElementById(`address-${id}`);
        card.querySelector(".address-view").classList.add("d-none");
        card.querySelector(".address-edit").classList.remove("d-none");
    });
});

// Hide edit address form when "cancel" button is clicked
document.querySelectorAll(".cancel-btn").forEach(button => {
    button.addEventListener("click", function () {
        const id = this.dataset.id;

        const card = document.getElementById(`address-${id}`);
        card.querySelector(".address-view").classList.remove("d-none");
        card.querySelector(".address-edit").classList.add("d-none");
    });
});