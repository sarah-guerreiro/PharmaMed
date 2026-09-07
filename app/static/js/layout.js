// AI assisted me in implementing the dynamic behaviour of the products menu dropdown,
// including desktop hover interactions, responsive behaviour, and closing the menu
// when clicking outside of it.

// Product dropdown
const toggle = document.querySelector(".products-toggle");
const productsMenu = document.querySelector(".products-menu");
const menu = new bootstrap.Collapse(document.getElementById("productsMenu"), { toggle: false });

// Check if the user is using a desktop
const isDesktop = () => window.matchMedia("(min-width: 992px)").matches;

// Open products menu on hover (desktop only)
toggle.addEventListener("mouseenter", () => {
    if (isDesktop()) {
        menu.show();
    }
});

productsMenu.addEventListener("mouseenter", () => {
    if (isDesktop()) {
        menu.show();
    }
});

// Close when mouse leaves the menu or button (desktop only)
const closeMenu = () => {
    if (isDesktop()) {
        setTimeout(() => {
            if (!toggle.matches(":hover") && !productsMenu.matches(":hover")) {
            menu.hide();
            }
        }, 200);
    }
};

toggle.addEventListener("mouseleave", closeMenu);
productsMenu.addEventListener("mouseleave", closeMenu);

// Close menu if click outside toggle and menu
document.addEventListener("click", function (event) {

    const productsMenuEl = document.getElementById("productsMenu");

    if (!isDesktop()) {
        if (
            !productsMenuEl.contains(event.target) &&
            !toggle.contains(event.target)
        ) {
            menu.hide();
        }
    }
});

// Add to cart button binding
document.querySelectorAll('.add-to-cart-btn').forEach(button => {
    button.addEventListener('click', function() {
        const productId = this.dataset.productId;
        addToCart(productId);
    });
});

function addToCart(productId) {
    fetch('/add_to_cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `product_id=${productId}&quantity=1`
    })
    .then(res => res.json())
    .then(data => {
        updateCartBadge(data.cart_count);
        addFlashMessage(data.message, data.category);
    });
}

function updateCartBadge (count) {
    const cartIcons = document.querySelectorAll('.cart-icon');

    cartIcons.forEach(icon => {
        let badge = icon.querySelector('.cart-badge');

        badge.innerText = count;

        if (count > 0) {
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    });
}

function addFlashMessage(message, category) {

    const container = document.querySelector('.flash-messages');
    const alertDiv = document.createElement('div');

    let alertClass = category === 'error' ? 'danger' : (category === 'persistent' ? 'info' : category);

    alertDiv.className = `alert alert-${alertClass} alert-dismissible fade d-flex align-items-center justify-content-center`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.dataset.persistent = (category === 'persistent') ? 'true' : 'false';
    alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    container.appendChild(alertDiv);

    // Trigger smooth fade in effect
    setTimeout(() => {
        alertDiv.classList.add('show');
    }, 100);

    // Auto-dismiss flash messages after 6 seconds
    if (alertDiv.dataset.persistent !== 'true') {
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 500);
        }, 6000);
    }
}