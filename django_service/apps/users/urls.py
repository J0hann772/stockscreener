"""
URL-маршруты для приложения users.

Маршруты:
    - /login/    — вход в аккаунт
    - /logout/   — выход из аккаунта
    - /register/ — регистрация нового пользователя
"""
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]
