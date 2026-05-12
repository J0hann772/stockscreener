document.addEventListener("DOMContentLoaded", function () {

    console.log("main.js подключен");

    // Переключение тёмной/светлой темы
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const root = document.documentElement;

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        root.setAttribute('data-bs-theme', 'dark');
        if (themeIcon) {
            themeIcon.classList.replace('bi-moon-stars', 'bi-sun');
        }
    } else {
        root.setAttribute('data-bs-theme', 'light');
        if (themeIcon) {
            themeIcon.classList.replace('bi-sun', 'bi-moon-stars');
        }
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const currentTheme = root.getAttribute('data-bs-theme');
            if (currentTheme === 'light') {
                root.setAttribute('data-bs-theme', 'dark');
                localStorage.setItem('theme', 'dark');

                if (themeIcon) {
                    themeIcon.classList.replace('bi-moon-stars', 'bi-sun');
                }

            } else {
                root.setAttribute('data-bs-theme', 'light');
                localStorage.setItem('theme', 'light');

                if (themeIcon) {
                    themeIcon.classList.replace('bi-sun', 'bi-moon-stars');
                }
            }
        });
    }

});


function showToast(message, isError = false) {
    const container = document.getElementById('toastContainer');
    if (!container) {
        alert(message);
        return;
    }
    const toastId = 'toast-' + Date.now();
    const bgClass = isError ? 'bg-danger text-white' : 'bg-success text-white';
    const html = `
        <div id="${toastId}" class="toast align-items-center ${bgClass}" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="true" data-bs-delay="3000">
            <div class="d-flex">
                <div class="toast-body">${escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
    const toastEl = document.getElementById(toastId);
    const bsToast = new bootstrap.Toast(toastEl);
    bsToast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : m === '<' ? '&lt;' : '&gt;');
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}