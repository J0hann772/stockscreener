"""
Утилиты для работы с JWT токенами.

Содержит функцию генерации JWT токена, подписанного RSA ключом (RS256).
"""
import jwt
import datetime
from django.conf import settings


def encode_jwt(user):
    """
    Генерирует JWT токен для пользователя.

    Создаёт токен с user_id и username в payload,
    подписывает приватным RSA ключом (алгоритм RS256).
    Время жизни токена задаётся в settings.JWT_TTL_MINUTES.

    Args:
        user (User): объект пользователя Django.

    Returns:
        str: подписанный JWT токен.
    """
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=getattr(settings, 'JWT_TTL_MINUTES', 60 * 24)),
        'iat': datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm='RS256')

    # Для RS256 нужен приватный ключ
    token = jwt.encode(
        payload,
        settings.JWT_PRIVATE_KEY,
        algorithm='RS256'
    )
    return token
