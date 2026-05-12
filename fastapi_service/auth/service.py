"""
Модуль аутентификации и авторизации для FastAPI.

Содержит функции для проверки JWT токенов (RS256),
извлечения пользователя из cookie, проверки внутренних
ключей между микросервисами и проверки прав доступа.
"""
import os
from fastapi import HTTPException, status, Request
import jwt

KEYS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'keys')
public_key_path = os.path.join(KEYS_DIR, 'public.pem')

if not os.path.exists(public_key_path):
    try:
        import subprocess
        import sys
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'generate_keys.py')
        if os.path.exists(script_path):
            print("Keys not found. Auto-generating via generate_keys.py...")
            subprocess.run([sys.executable, script_path], check=True)
    except Exception as e:
        print(f"Warning: Could not auto-generate keys: {e}")

try:
    with open(public_key_path, 'rb') as f:
        PUBLIC_KEY = f.read()
except FileNotFoundError:
    PUBLIC_KEY = b""


def verify_jwt_token(token):
    """
    Проверяет и декодирует JWT токен.

    Использует публичный RSA ключ для проверки подписи (RS256).

    Args:
        token (str): JWT токен для проверки.

    Returns:
        dict: payload из токена (user_id, username и т.д.).

    Raises:
        HTTPException: 401 если токен истёк или невалиден.
    """
    try:
        return jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])

    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired") from exc

    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token") from exc


def get_user(request: Request):
    """
    Извлекает данные пользователя из JWT cookie.

    Ищет токен в cookie 'access_token' (для фронтенда Django).

    Args:
        request (Request): объект запроса FastAPI.

    Returns:
        dict: payload из токена с данными пользователя.

    Raises:
        HTTPException: 401 если cookie отсутствует.
    """
    # Ищем токен только в куках (для фронтенда Django)
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token")

    return verify_jwt_token(token)


def verify_internal_key(request: Request):
    """
    Проверяет внутренний ключ для межсервисного взаимодействия.

    Используется для запросов от Django к FastAPI.
    Проверяет заголовок X-Internal-Key.

    Args:
        request (Request): объект запроса FastAPI.

    Returns:
        bool: True если ключ валиден.

    Raises:
        HTTPException: 403 если ключ отсутствует или невалиден.
    """
    internal_key = request.headers.get("X-Internal-Key")
    expected_key = os.getenv("INTERNAL_API_KEY", "default-internal-key-for-dev")#В проде из .env

    if not internal_key or internal_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing internal key"
        )
    return True


def check_permission(payload, required_permissions):
    """
    Проверяет, есть ли у пользователя нужные права доступа.

    Args:
        payload (dict): payload из JWT токена.
        required_permissions (list): список необходимых прав.

    Returns:
        bool: True если хотя бы одно из прав есть у пользователя.

    Raises:
        HTTPException: 403 если прав недостаточно.
    """
    user_permissions = payload.get("permissions", [])
    if any(permission in user_permissions for permission in required_permissions):
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have enough rights")
