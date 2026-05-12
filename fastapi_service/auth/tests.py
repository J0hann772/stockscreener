"""
Тесты модуля аутентификации и авторизации.
"""

from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import jwt

from fastapi_service.auth.service import(
    verify_jwt_token,
    get_user,
    verify_internal_key,
    check_permission)


def test_verify_jwt_valid():
    """
    Проверяет, корректная ли декодировка валидного JWT токена.
    """
    with patch("fastapi_service.auth.service.jwt.decode") as mock_decode:
        mock_decode.return_value = {"user_id": 1}
        result = verify_jwt_token("token123")

        assert result["user_id"] == 1


def test_verify_jwt_expired():
    """
    Проверяет обработку истёкшего JWT токена.
    """
    with patch("fastapi_service.auth.service.jwt.decode") as mock_decode:
        mock_decode.side_effect = jwt.ExpiredSignatureError()

        try:
            verify_jwt_token("token123")
            assert False
        except HTTPException as e:
            assert e.status_code == 401


def test_verify_jwt_invalid():
    """
    Проверяет обработку невалидного JWT токена.
    """
    with patch("fastapi_service.auth.service.jwt.decode") as mock_decode:
        mock_decode.side_effect = jwt.InvalidTokenError()

        try:
            verify_jwt_token("token123")
            assert False
        except HTTPException as e:
            assert e.status_code == 401


def test_get_user_success():
    """
    Проверяет успешное получение пользователя из cookie.
    """
    request = MagicMock()
    request.cookies = {"access_token": "token123"}

    with patch(
        "fastapi_service.auth.service.verify_jwt_token", 
        return_value={"user": 1}):
        result = get_user(request)

    assert result["user"] == 1


def test_get_user_missing_token():
    """
    При отсутствии токена в cookie выбрасывается ошибка.
    """
    request = MagicMock()
    request.cookies = {}

    try:
        get_user(request)
        assert False
    except HTTPException as e:
        assert e.status_code == 401


def test_internal_key_valid():
    """
    Проверяет успешную валидацию internal API key.
    """
    request = MagicMock()
    request.headers = {"X-Internal-Key": "default-internal-key-for-dev"}
    result = verify_internal_key(request)

    assert result is True


def test_internal_key_invalid():
    """
    Проверяет отказ при неверном internal API key.
    """
    request = MagicMock()
    request.headers = {"X-Internal-Key": "wrong"}

    try:
        verify_internal_key(request)
        assert False
    except HTTPException as e:
        assert e.status_code == 403


def test_permission_ok():
    """
    Проверяет успешную проверку прав доступа.
    """
    payload = {"permissions": ["read", "write"]}
    result = check_permission(payload, ["read"])

    assert result is True


def test_permission_denied():
    """
    Проверяет отказ при отсутствии нужных прав.
    """
    payload = {"permissions": ["read"]}

    try:
        check_permission(payload, ["admin"])
        assert False
    except HTTPException as e:
        assert e.status_code == 403
