
document.addEventListener("DOMContentLoaded", function () {

    // Automatically dismiss success and info alerts after 5 seconds.
    const alerts = document.querySelectorAll(
        ".alert-success, .alert-info"
    );

    alerts.forEach(function (alert) {
        setTimeout(function () {
            if (document.body.contains(alert)) {
                alert.style.transition = "opacity 0.5s ease";
                alert.style.opacity = "0";

                setTimeout(function () {
                    alert.remove();
                }, 500);
            }
        }, 5000);
    });

    // Prevent accidental multiple form submissions.
    const forms = document.querySelectorAll("form");

    forms.forEach(function (form) {
        form.addEventListener("submit", function () {
            if (!form.checkValidity()) {
                return;
            }

            const submitButton = form.querySelector(
                'button[type="submit"], input[type="submit"]'
            );

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = "Processing...";
            }
        });
    });

    // Confirm actions on forms marked with data-confirm.
    const confirmForms = document.querySelectorAll(
        "form[data-confirm]"
    );

    confirmForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const message = form.getAttribute("data-confirm");

            if (message && !window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

});
