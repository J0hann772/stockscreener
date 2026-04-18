"""
Модуль с представлениями (views) для авторизации и регистрации пользователей.

Содержит views для входа, регистрации и выхода из аккаунта.
При входе/регистрации генерируется JWT токен и сохраняется в cookie.
"""
from django.shortcuts import render
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from .forms import RegistrationForm
from .utils import encode_jwt


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
            
            # Генерация JWT и установка Cookie
            token = encode_jwt(user)
            response = redirect('ticker_list')
            response.set_cookie(
                'access_token', 
                token, 
                httponly=True,
                samesite='Lax'
            )
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
    if request.method == "POST": 
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Генерация JWT и установка Cookie
            token = encode_jwt(user)
            response = redirect('ticker_list')
            response.set_cookie(
                'access_token', 
                token, 
                httponly=True,
                samesite='Lax'
            )
            return response
    else:
        form = RegistrationForm()
    return render(request, "users/register.html", {"form": form})


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
