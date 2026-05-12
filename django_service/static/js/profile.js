// Скрипт для страницы профиля (обработка форм через AJAX)

document.addEventListener('DOMContentLoaded', function() {
    // Функции showToast и getCookie берутся из main.js (глобальные)

    function handleForm(form, onSuccess = null) {
        if (!form) return;
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(form);
            fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: formData
            })
            .then(response => response.json().then(data => ({ status: response.status, body: data })))
            .then(({ status, body }) => {
                if (status === 200 && body.success) {
                    showToast(body.message, false);
                    if (onSuccess) onSuccess(body);
                    if (form.id === 'topupForm' || form.id === 'balanceForm') {
                        // Обновляем отображение баланса без перезагрузки страницы
                        fetch(window.location.href)
                            .then(res => res.text())
                            .then(html => {
                                const parser = new DOMParser();
                                const doc = parser.parseFromString(html, 'text/html');
                                const newBalance = doc.querySelector('#currentBalance')?.innerText;
                                if (newBalance) document.getElementById('currentBalance').innerText = newBalance;
                            })
                            .catch(err => console.error('Не удалось обновить баланс', err));
                    }
                } else {
                    let errorMsg = body.message || 'Ошибка';
                    if (body.errors) {
                        if (typeof body.errors === 'object') errorMsg = Object.values(body.errors).join(', ');
                        else errorMsg = body.errors;
                    }
                    showToast(errorMsg, true);
                }
            })
            .catch(err => {
                console.error('Fetch error:', err);
                showToast('Сетевая ошибка', true);
            });
        });
    }

    // Инициализация форм
    handleForm(document.getElementById('profileForm'));
    handleForm(document.getElementById('topupForm'));
    handleForm(document.getElementById('balanceForm'));
    handleForm(document.getElementById('passwordForm'));
});