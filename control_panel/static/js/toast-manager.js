/**
 * Toast Manager - Bootstrap 5 Toast Notifications
 * Provides user feedback for service control actions
 */
class ToastManager {
    constructor() {
        this.container = document.querySelector('.toast-container');
        this.toastCounter = 0;
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Toast type: success, error, info, warning
     * @param {number} duration - Duration in milliseconds (default: 5000)
     */
    show(message, type = 'success', duration = 5000) {
        const toastId = `toast-${++this.toastCounter}`;
        const toastElement = this.createToastElement(toastId, message, type);

        this.container.appendChild(toastElement);

        // Initialize Bootstrap toast
        const toast = new bootstrap.Toast(toastElement, {
            delay: duration
        });

        // Show the toast
        toast.show();

        // Remove from DOM after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });

        return toast;
    }

    /**
     * Show service action feedback
     * @param {string} service - Service name
     * @param {string} action - Action performed
     * @param {string} status - success or error
     * @param {string} errorMessage - Optional error message
     */
    showServiceAction(service, action, status, errorMessage = null) {
        const messages = {
            start: {
                success: `Started ${service} successfully`,
                error: `Failed to start ${service}`
            },
            stop: {
                success: `Stopped ${service} successfully`,
                error: `Failed to stop ${service}`
            },
            restart: {
                success: `Restarted ${service} successfully`,
                error: `Failed to restart ${service}`
            },
            enable: {
                success: `Auto-start enabled for ${service}`,
                error: `Failed to enable auto-start for ${service}`
            },
            disable: {
                success: `Auto-start disabled for ${service}`,
                error: `Failed to disable auto-start for ${service}`
            },
            delete: {
                success: `Deleted ${service} successfully`,
                error: `Failed to delete ${service}`
            }
        };

        let message = messages[action]?.[status] || `${action} ${service}: ${status}`;

        // Add error details if provided
        if (status === 'error' && errorMessage) {
            message += `: ${errorMessage}`;
        }

        this.show(message, status);
    }

    /**
     * Create toast HTML element
     * @param {string} id - Unique toast ID
     * @param {string} message - Toast message
     * @param {string} type - Toast type
     * @returns {HTMLElement} Toast element
     */
    createToastElement(id, message, type) {
        const toast = document.createElement('div');
        toast.id = id;
        toast.className = 'toast';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        const icon = this.getIcon(type);
        const bgClass = this.getBackgroundClass(type);

        toast.innerHTML = `
            <div class="toast-header ${bgClass} text-white">
                <span class="me-2">${icon}</span>
                <strong class="me-auto">Control Panel</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;

        return toast;
    }

    /**
     * Get icon for toast type
     * @param {string} type - Toast type
     * @returns {string} Icon HTML
     */
    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✗',
            info: 'ℹ',
            warning: '⚠'
        };
        return icons[type] || icons.info;
    }

    /**
     * Get Bootstrap background class for toast type
     * @param {string} type - Toast type
     * @returns {string} Bootstrap class
     */
    getBackgroundClass(type) {
        const classes = {
            success: 'bg-success',
            error: 'bg-danger',
            info: 'bg-info',
            warning: 'bg-warning'
        };
        return classes[type] || classes.info;
    }
}

// Initialize global toast manager
window.toastManager = new ToastManager();

// Parse URL parameters for action feedback on page load
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const action = urlParams.get('action');
    const service = urlParams.get('service');
    const status = urlParams.get('status');
    const message = urlParams.get('message');

    if (action && service && status) {
        window.toastManager.showServiceAction(service, action, status, message);

        // Clean up URL parameters
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }
});
