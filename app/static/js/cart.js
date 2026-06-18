// Update cart badge count, cart item quantity, total items, item total and cart total
document.querySelectorAll('.increase-btn, .decrease-btn, .remove-btn').forEach(button => {
    button.addEventListener('click', function () {

        const productId = this.dataset.productId;
        const action = this.dataset.action;

        fetch('/update_cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `product_id=${productId}&action=${action}`
        })
        .then(res => res.json())
        .then(data => {
            console.log(data);

            // Update cart badge count
            updateCartBadge(data.cart_count);

            // Remove or update cart item quantity
            const itemId = data.product_id;
            const quantityValue = document.querySelector(`.quantity-value[data-product-id="${itemId}"]`);

            if (data.updated_quantity > 0) {
                quantityValue.innerText = data.updated_quantity;
            } else {
                quantityValue.closest('.cart-body').remove();
            }

            // Disable "+" button if max stock is reached
            const increaseButton = document.querySelector(`.increase-btn[data-product-id="${itemId}"]`);

            if (increaseButton) {
                if (data.updated_quantity >= data.stock) {
                    increaseButton.disabled = true;
                } else {
                    increaseButton.disabled = false;
                }
            }

            // Update total number of items
            const totalItems = document.querySelector('.total-items');
            if (totalItems) {
                totalItems.innerText = "Items: " + data.cart_count;
            }

            // Update item total
            const itemTotal = document.querySelector(`.item-total[data-product-id="${itemId}"]`);
            if (itemTotal) {
                itemTotal.innerText = "€ " + data.item_total.toFixed(2);
            }

            // Update cart total
            const cartTotal = document.querySelector('.cart-total');
            if (cartTotal) {
                cartTotal.innerText = "Total: € " + data.cart_total.toFixed(2);
            }

            // If cart is empty
            if (data.cart_count === 0) {

                if (totalItems) totalItems.remove();
                if (cartTotal) cartTotal.closest('.cart-bottom').remove();

                if (!document.querySelector('.empty-cart')) {
                    const container = document.querySelector('.container');
                    const emptyDiv = document.createElement('div');
                    emptyDiv.className = 'empty-cart pt-3';

                    emptyDiv.innerHTML = `
                        <p>Your cart is empty</p>
                        <div class="empty-cart-image d-flex justify-content-center align-items-center mt-5">
                            <img src="/static/images/empty_cart.png" id="emptyCart" alt="Empty cart">
                        </div>
                    `;

                    container.appendChild(emptyDiv);
                }

                const buyButton = document.querySelector('.checkout-button');
                buyButton.remove();
            }
        });
    });
});