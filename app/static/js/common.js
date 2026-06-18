// Trigger smooth fade in effect for flash messages
document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
        alert.classList.add('show');
    }, 100);
});

// Auto-dismiss flash messages after 6 seconds
setTimeout(() => {
    document.querySelectorAll('.alert').forEach(alert => {

        // Skip for persistent alerts
        if (alert.dataset.persistent === 'true') return;

        alert.classList.remove('show');

        setTimeout(() => {
            alert.remove();
        }, 500);
        
    });
}, 6000);

// Set current year on copyright
document.getElementById("copyright").innerHTML = new Date().getFullYear() + " | PharmaMed. All rights reserved.";