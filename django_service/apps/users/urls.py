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
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/topup/', views.topup_balance, name='topup_balance'),
    path('profile/set_balance/', views.set_balance, name='set_balance'),
    path('profile/change_password/', views.change_password, name='change_password'),
    path('profile/change_username/', views.change_username, name='change_username'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]
