"""
Декоратор для защиты Django views с помощью JWT (RS256).

Проверяет наличие и валидность Bearer-токена в заголовке Authorization.
"""
import jwt
from functools import wraps
from django.http import JsonResponse
from django.conf import settings


def jwt_rs256_required(func):
    """
    Декоратор, который требует валидный JWT токен.

    Извлекает токен из заголовка Authorization (формат: Bearer <token>),
    проверяет подпись публичным RSA ключом и добавляет
    данные из токена в request.user_claims.

    Args:
        func (callable): view-функция Django.

    Returns:
        callable: обёрнутая функция с проверкой JWT.
    """
    @wraps(func)
    def decorated(request, *args, **kwargs):
        """
        Внутренняя функция-обёртка для проверки токена.

        Args:
            request (HttpRequest): объект запроса Django.

        Returns:
            JsonResponse: ошибка 401 если токен невалиден.
            HttpResponse: результат оригинальной view при успехе.
        """
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Token missing'}, status=401)

        token = auth_header.split(' ')[1]

        try:
            # Для RS256 вторым аргументом передаем публичный ключ
            # Он должен начинаться с -----BEGIN PUBLIC KEY-----
            payload = jwt.decode(
                token,
                settings.JWT_PUBLIC_KEY,
                algorithms=['RS256']
            )
            request.user_claims = payload
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=401)
        except (jwt.InvalidTokenError, jwt.InvalidKeyError) as e:
            return JsonResponse({'error': str(e)}, status=401)

        return func(request, *args, **kwargs)

    return decorated