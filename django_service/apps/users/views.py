"""
Представления для авторизации, регистрации и управления профилем.

Содержит views для входа, регистрации и выхода из аккаунта.
При входе/регистрации генерируется JWT токен и сохраняется в cookie.
"""
import json
import logging

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import BalanceTopUpForm, BalanceUpdateForm, ProfileUpdateForm, RegistrationForm
from .models import Profile
from .utils import encode_jwt

logger = logging.getLogger('apps.users')


def login_view(request):
    """
    Обрабатывает вход пользователя в систему.

    GET-запрос — показывает форму входа.
    POST-запрос — проверяет логин/пароль, при успехе создаёт
    JWT токен и ставит его в cookie.

    Args:
        request (HttpRequest): объект запроса Django.

    Returns:
        HttpResponse: редирект на список тикеров при успехе,
            либо страница с формой входа.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            token = encode_jwt(user)
            response = redirect('ticker_list')
            response.set_cookie('access_token', token, httponly=True, samesite='Lax')
            return response
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})


def register_view(request):
    """
    Обрабатывает регистрацию нового пользователя.

    GET-запрос — показывает форму регистрации.
    POST-запрос — создаёт нового пользователя, логинит его
    и ставит JWT токен в cookie.

    Args:
        request (HttpRequest): объект запроса Django.

    Returns:
        HttpResponse: редирект на список тикеров при успехе,
            либо страница с формой регистрации.
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            token = encode_jwt(user)
            response = redirect('ticker_list')
            response.set_cookie('access_token', token, httponly=True, samesite='Lax')
            return response
    else:
        form = RegistrationForm()
    return render(request, 'users/register.html', {'form': form})


def logout_view(request):
    """
    Выход пользователя из системы.

    Завершает сессию и удаляет JWT cookie.

    Args:
        request (HttpRequest): объект запроса Django.

    Returns:
        HttpResponse: редирект на страницу входа.
    """
    logout(request)
    response = redirect('login')
    response.delete_cookie('access_token')
    return response


@login_required
def profile_view(request):
    """
    Отображает страницу профиля и обрабатывает POST-формы.

    Поддерживает обновление профиля, баланса, пополнение баланса
    и смену пароля через AJAX (X-Requested-With: XMLHttpRequest).

    Args:
        request (HttpRequest): объект запроса Django.

    Returns:
        HttpResponse: страница профиля или JsonResponse при AJAX.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if 'update_profile' in request.POST:
            form = ProfileUpdateForm(request.POST, instance=profile, user=request.user)
            if form.is_valid():
                form.save()
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Профиль обновлён'})
                messages.success(request, 'Профиль обновлён')
                return redirect('profile')
            if is_ajax:
                return JsonResponse(
                    {'success': False, 'message': 'Ошибка в форме', 'errors': form.errors},
                    status=400
                )
            return redirect('profile')

        if 'update_balance' in request.POST:
            form = BalanceUpdateForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Баланс обновлён'})
                return redirect('profile')
            if is_ajax:
                return JsonResponse(
                    {'success': False, 'message': 'Ошибка в форме', 'errors': form.errors},
                    status=400
                )
            return redirect('profile')

        if 'topup_balance' in request.POST:
            form = BalanceTopUpForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data['amount']
                profile.balance += amount
                profile.save()
                if is_ajax:
                    return JsonResponse({'success': True, 'message': f'Баланс пополнен на {amount} ₽'})
                return redirect('profile')
            if is_ajax:
                return JsonResponse(
                    {'success': False, 'message': 'Неверная сумма', 'errors': form.errors},
                    status=400
                )
            return redirect('profile')

        if 'change_password' in request.POST:
            form = PasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Пароль успешно изменён'})
                messages.success(request, 'Пароль изменён')
                return redirect('profile')
            if is_ajax:
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse(
                    {'success': False, 'message': 'Ошибка смены пароля', 'errors': errors},
                    status=400
                )
            return redirect('profile')

        return JsonResponse({'success': False, 'message': 'Неизвестное действие'}, status=400)

    # GET
    context = {
        'profile': profile,
        'profile_form': ProfileUpdateForm(instance=profile, user=request.user),
        'balance_form': BalanceUpdateForm(instance=profile),
        'topup_form': BalanceTopUpForm(),
        'password_form': PasswordChangeForm(user=request.user),
    }
    return render(request, 'users/profile.html', context)


@login_required
def update_profile(request):
    """Обновляет профиль пользователя через AJAX POST."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не разрешён'}, status=405)
    profile = request.user.profile
    form = ProfileUpdateForm(request.POST, instance=profile, user=request.user)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Профиль обновлён'})
    errors = {field: error[0] for field, error in form.errors.items()}
    return JsonResponse({'success': False, 'errors': errors}, status=400)


@login_required
def topup_balance(request):
    """Пополняет баланс пользователя через AJAX POST."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не разрешён'}, status=405)
    profile = request.user.profile
    form = BalanceTopUpForm(request.POST)
    if form.is_valid():
        amount = form.cleaned_data['amount']
        profile.balance += amount
        profile.save()
        return JsonResponse({'success': True, 'message': f'Баланс пополнен на {amount} ₽'})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
def set_balance(request):
    """Устанавливает точное значение баланса через AJAX POST."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не разрешён'}, status=405)
    profile = request.user.profile
    form = BalanceUpdateForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Баланс обновлён'})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_http_methods(["POST"])
def change_password(request):
    """
    Меняет пароль пользователя через AJAX POST.

    Args:
        request (HttpRequest): POST-запрос с полями текущего и нового пароля.

    Returns:
        JsonResponse: {'success': True} или {'success': False, 'errors': {...}}.
    """
    form = PasswordChangeForm(user=request.user, data=request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        return JsonResponse({'success': True, 'message': 'Пароль успешно изменён'})
    errors = {field: error[0] for field, error in form.errors.items()}
    return JsonResponse({'success': False, 'errors': errors}, status=400)


@login_required
@require_http_methods(["POST"])
def change_username(request):
    """
    Меняет имя пользователя через AJAX POST.

    Args:
        request (HttpRequest): POST-запрос с JSON {'username': str}.

    Returns:
        JsonResponse: {'success': True} или {'success': False, 'message': str}.
    """
    try:
        data = json.loads(request.body)
    except (ValueError, json.JSONDecodeError):
        data = request.POST
    new_username = (data.get('username') or '').strip()
    if not new_username:
        return JsonResponse({'success': False, 'message': 'Имя не может быть пустым'}, status=400)
    if len(new_username) < 3:
        return JsonResponse({'success': False, 'message': 'Минимум 3 символа'}, status=400)
    if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
        return JsonResponse({'success': False, 'message': 'Это имя уже занято'}, status=400)
    request.user.username = new_username
    request.user.save()
    logger.info("Пользователь %s сменил имя на %s", request.user.pk, new_username)
    return JsonResponse({'success': True, 'message': 'Имя изменено'})