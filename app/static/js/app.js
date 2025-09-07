// Wallet Manager Frontend JavaScript

// Utility functions
function formatWalletAddress(address) {
    if (address.length !== 42) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}

function getScoreClass(score) {
    if (score >= 8) return 'score-high';
    if (score >= 5) return 'score-medium';
    return 'score-low';
}

// Toast notification function
function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toastId = 'toast-' + Date.now();
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toast = new bootstrap.Toast(document.getElementById(toastId));
    toast.show();
    
    setTimeout(() => {
        document.getElementById(toastId)?.remove();
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1050';
    document.body.appendChild(container);
    return container;
}

// HTMX event handlers
document.body.addEventListener('htmx:beforeRequest', function(event) {
    const target = event.target;
    if (target.classList.contains('btn')) {
        target.classList.add('disabled');
        const originalText = target.innerHTML;
        target.dataset.originalText = originalText;
        target.innerHTML = originalText + ' <span class="spinner-border spinner-border-sm loading-spinner"></span>';
    }
});

document.body.addEventListener('htmx:afterRequest', function(event) {
    const target = event.target;
    if (target.classList.contains('btn') && target.dataset.originalText) {
        target.classList.remove('disabled');
        target.innerHTML = target.dataset.originalText;
        delete target.dataset.originalText;
    }
    
    const xhr = event.detail.xhr;
    if (xhr.status === 201) {
        showToast('Success!', 'Operation completed successfully', 'success');
    } else if (xhr.status === 400) {
        showToast('Error', 'Invalid data provided', 'error');
    } else if (xhr.status === 404) {
        showToast('Not Found', 'Resource not found', 'error');
    } else if (xhr.status >= 500) {
        showToast('Server Error', 'Something went wrong on our end', 'error');
    }
});

document.body.addEventListener('htmx:responseError', function(event) {
    showToast('Request Failed', 'Failed to connect to server', 'error');
});

// Wallet operations
function deleteWallet(walletId) {
    if (confirm('Are you sure you want to delete this wallet? This action cannot be undone.')) {
        fetch(`/wallets/${walletId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                showToast('Success', 'Wallet deleted successfully', 'success');
                htmx.trigger('#wallets-list', 'load');
            } else {
                showToast('Error', 'Failed to delete wallet', 'error');
            }
        })
        .catch(() => {
            showToast('Error', 'Failed to delete wallet', 'error');
        });
    }
}

// Form validation helpers
function validateEthereumAddress(address) {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
}

function validateScore(score) {
    const num = parseInt(score);
    return !isNaN(num) && num >= 0 && num <= 10;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add Ethereum address validation to all address inputs
    document.querySelectorAll('input[name="address"]').forEach(input => {
        input.addEventListener('input', function(e) {
            const address = e.target.value;
            const isValid = validateEthereumAddress(address);
            
            if (address.length > 0 && !isValid) {
                e.target.setCustomValidity('Invalid Ethereum address format');
                e.target.classList.add('is-invalid');
            } else {
                e.target.setCustomValidity('');
                e.target.classList.remove('is-invalid');
            }
        });
    });
    
    // Add score validation
    document.querySelectorAll('input[name="score"]').forEach(input => {
        input.addEventListener('input', function(e) {
            const score = e.target.value;
            const isValid = validateScore(score);
            
            if (score.length > 0 && !isValid) {
                e.target.setCustomValidity('Score must be between 0 and 10');
                e.target.classList.add('is-invalid');
            } else {
                e.target.setCustomValidity('');
                e.target.classList.remove('is-invalid');
            }
        });
    });
});

// Global functions for HTMX templates
window.deleteWallet = deleteWallet;
window.showToast = showToast;