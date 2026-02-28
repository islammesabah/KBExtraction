/**
 * Global Toast Helper (Bootstrap 5)
 * ----------------------------------
 * Clean replacement for alert().
 * Supports: success, error, warning, info.
 */

const container = document.querySelector(".toast-container");

/**
 * Show a Bootstrap toast.
 *
 * @param {Object} opts
 * @param {"success"|"error"|"warning"|"info"} opts.type
 * @param {string} opts.title
 * @param {string} opts.message
 * @param {number} [opts.delay=4000]
 */
export function showToast({ type = "info", title = "", message = "", delay = 4000 }) {
    if (!container || !window.bootstrap) return;

    const config = {
        success: {
            headerClass: "text-bg-success",
            icon: "bi-check-circle-fill",
        },
        error: {
            headerClass: "text-bg-danger",
            icon: "bi-x-circle-fill",
        },
        warning: {
            headerClass: "text-bg-warning",
            icon: "bi-exclamation-triangle-fill",
        },
        info: {
            headerClass: "text-bg-primary",
            icon: "bi-info-circle-fill",
        },
    };

    const { headerClass, icon } = config[type] || config.info;

    const toastEl = document.createElement("div");
    toastEl.className = "toast align-items-center border-0";
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");

    toastEl.innerHTML = `
    <div class="toast-header ${headerClass}">
      <i class="bi ${icon} me-2"></i>
      <strong class="me-auto">${title}</strong>
      <button type="button" class="btn-close btn-close-white ms-2 mb-1"
        data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
    <div class="toast-body bg-white">
      ${message}
    </div>
  `;

    container.appendChild(toastEl);

    const toast = new bootstrap.Toast(toastEl, {
        delay,
    });

    toast.show();

    // Clean up DOM after hidden
    toastEl.addEventListener("hidden.bs.toast", () => {
        toastEl.remove();
    });
}
