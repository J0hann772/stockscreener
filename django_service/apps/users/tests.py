"""
Тесты для вспомогательных модулей users: auth.py, utils.py.

Используется стандартная библиотека unittest через Django TestCase.
Запуск: python manage.py test apps.users
"""
import datetime
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from .forms import BalanceTopUpForm, BalanceUpdateForm, RegistrationForm
from .models import Profile


class ProfileSignalTest(TestCase):
    """Тесты автоматического создания Profile через сигнал post_save."""

    def test_profile_created_on_user_create(self):
        """Profile создаётся автоматически при создании User."""
        user = User.objects.create_user(
            username='siguser', password='pass12345'
        )
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_profile_str(self):
        """__str__ профиля содержит имя пользователя."""
        user = User.objects.create_user(
            username='struser', password='pass12345'
        )
        self.assertIn('struser', str(user.profile))

    def test_profile_default_balance(self):
        """Баланс нового профиля равен 0."""
        user = User.objects.create_user(
            username='baluser', password='pass12345'
        )
        self.assertEqual(user.profile.balance, Decimal('0.00'))

    def test_profile_one_to_one_relation(self):
        """У одного пользователя ровно один профиль."""
        user = User.objects.create_user(
            username='otouser', password='pass12345'
        )
        count = Profile.objects.filter(user=user).count()
        self.assertEqual(count, 1)


class RegistrationFormTest(TestCase):
    """Тесты формы RegistrationForm."""

    def test_valid_form(self):
        """Корректные данные делают форму валидной."""
        form = RegistrationForm(data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertTrue(form.is_valid())

    def test_email_required(self):
        """Без email форма невалидна."""
        form = RegistrationForm(data={
            'username': 'newuser2',
            'email': '',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_mismatch(self):
        """Разные пароли делают форму невалидной."""
        form = RegistrationForm(data={
            'username': 'newuser3',
            'email': 'x@x.com',
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass!',
        })
        self.assertFalse(form.is_valid())

    def test_save_sets_email(self):
        """save() сохраняет email в объект пользователя."""
        form = RegistrationForm(data={
            'username': 'emailuser',
            'email': 'test@mail.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.email, 'test@mail.com')


class BalanceFormsTest(TestCase):
    """Тесты форм баланса."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='balformuser', password='pass12345'
        )
        self.profile = self.user.profile

    def test_balance_update_negative_invalid(self):
        """Отрицательный баланс не проходит валидацию."""
        form = BalanceUpdateForm(
            data={'balance': '-100'}, instance=self.profile
        )
        self.assertFalse(form.is_valid())
        self.assertIn('balance', form.errors)

    def test_balance_update_zero_valid(self):
        """Нулевой баланс допустим."""
        form = BalanceUpdateForm(
            data={'balance': '0'}, instance=self.profile
        )
        self.assertTrue(form.is_valid())

    def test_balance_topup_valid(self):
        """Корректная сумма пополнения проходит валидацию."""
        form = BalanceTopUpForm(data={'amount': '500.00'})
        self.assertTrue(form.is_valid())

    def test_balance_topup_zero_invalid(self):
        """Ноль — невалидная сумма (min_value=0.01)."""
        form = BalanceTopUpForm(data={'amount': '0'})
        self.assertFalse(form.is_valid())

    def test_balance_topup_negative_invalid(self):
        """Отрицательная сумма пополнения невалидна."""
        form = BalanceTopUpForm(data={'amount': '-50'})
        self.assertFalse(form.is_valid())


class RegisterViewTest(TestCase):
    """Тесты view register_view."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('register')

    def test_get_returns_200(self):
        """GET отдаёт страницу регистрации."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_creates_user_and_redirects(self):
        """POST с корректными данными создаёт пользователя и редиректит."""
        response = self.client.post(self.url, {
            'username': 'reguser',
            'email': 'reg@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='reguser').exists())

    def test_post_invalid_data_stays_on_page(self):
        """POST с некорректными данными остаётся на странице (200)."""
        response = self.client.post(self.url, {
            'username': '',
            'email': 'bad-email',
            'password1': '123',
            'password2': '456',
        })
        self.assertEqual(response.status_code, 200)


class LoginViewTest(TestCase):
    """Тесты view login_view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='loginuser', password='pass12345'
        )
        self.client = Client()
        self.url = reverse('login')

    def test_get_returns_200(self):
        """GET отдаёт страницу входа."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_credentials_redirects(self):
        """POST с правильными данными редиректит."""
        response = self.client.post(self.url, {
            'username': 'loginuser',
            'password': 'pass12345',
        })
        self.assertEqual(response.status_code, 302)

    def test_post_valid_sets_jwt_cookie(self):
        """POST с правильными данными устанавливает access_token cookie."""
        response = self.client.post(self.url, {
            'username': 'loginuser',
            'password': 'pass12345',
        })
        self.assertIn('access_token', response.cookies)

    def test_post_wrong_password_stays(self):
        """POST с неверным паролем остаётся на странице входа."""
        response = self.client.post(self.url, {
            'username': 'loginuser',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)


class LogoutViewTest(TestCase):
    """Тесты view logout_view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='logoutuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='logoutuser', password='pass12345')

    def test_logout_redirects(self):
        """Выход редиректит (302)."""
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)


class ChangeUsernameViewTest(TestCase):
    """Тесты view change_username."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='origname', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='origname', password='pass12345')
        self.url = reverse('change_username')

    def test_change_username_success(self):
        """Успешная смена имени возвращает success=True."""
        response = self.client.post(
            self.url,
            data=json.dumps({'username': 'newname'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newname')

    def test_change_username_too_short(self):
        """Имя короче 3 символов возвращает ошибку 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({'username': 'ab'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_change_username_taken(self):
        """Занятое имя возвращает ошибку 400."""
        User.objects.create_user(username='takenname', password='pass12345')
        response = self.client.post(
            self.url,
            data=json.dumps({'username': 'takenname'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_change_username_empty(self):
        """Пустое имя возвращает ошибку 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({'username': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


class TopupBalanceViewTest(TestCase):
    """Тесты view topup_balance."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='topupuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='topupuser', password='pass12345')
        self.url = reverse('topup_balance')

    def test_topup_increases_balance(self):
        """Пополнение баланса увеличивает его на указанную сумму."""
        response = self.client.post(self.url, {'amount': '200.00'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.balance, Decimal('200.00'))

    def test_topup_invalid_amount(self):
        """Некорректная сумма возвращает 400."""
        response = self.client.post(self.url, {'amount': '-50'})
        self.assertEqual(response.status_code, 400)

    def test_topup_get_not_allowed(self):
        """GET возвращает 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class SetBalanceViewTest(TestCase):
    """Тесты view set_balance."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='setbaluser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='setbaluser', password='pass12345')
        self.url = reverse('set_balance')

    def test_set_balance_success(self):
        """POST устанавливает точное значение баланса."""
        response = self.client.post(self.url, {'balance': '1000.00'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.balance, Decimal('1000.00'))

    def test_set_balance_negative_invalid(self):
        """Отрицательный баланс возвращает 400."""
        response = self.client.post(self.url, {'balance': '-1'})
        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        """GET возвращает 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class JwtAuthDecoratorTest(TestCase):
    """Тесты декоратора jwt_rs256_required из users/auth.py."""

    def setUp(self):
        from django.http import HttpResponse
        from apps.users.auth import jwt_rs256_required

        @jwt_rs256_required
        def dummy_view(request):
            return HttpResponse('ok')

        self.factory = RequestFactory()
        self.view = dummy_view

    def test_missing_header_returns_401(self):
        """Запрос без заголовка Authorization возвращает 401."""
        request = self.factory.get('/fake/')
        response = self.view(request)
        self.assertEqual(response.status_code, 401)

    def test_wrong_format_returns_401(self):
        """Заголовок не в формате 'Bearer ...' возвращает 401."""
        request = self.factory.get('/fake/', HTTP_AUTHORIZATION='Token abc123')
        response = self.view(request)
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_returns_401(self):
        """Невалидный JWT токен возвращает 401."""
        request = self.factory.get(
            '/fake/', HTTP_AUTHORIZATION='Bearer invalidtoken'
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 401)

    def test_valid_token_calls_view(self):
        """Валидный JWT токен пропускает запрос в view."""
        from apps.users.utils import encode_jwt
        user = User.objects.create_user(username='jwtuser', password='pass12345')
        token = encode_jwt(user)
        request = self.factory.get(
            '/fake/', HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 200)


class EncodeJwtTest(TestCase):
    """Тесты функции encode_jwt из users/utils.py."""

    def test_returns_string(self):
        """encode_jwt возвращает строку."""
        from apps.users.utils import encode_jwt
        user = User.objects.create_user(
            username='jwttest', password='pass12345'
        )
        token = encode_jwt(user)
        self.assertIsInstance(token, str)

    def test_token_decodable(self):
        """Сгенерированный токен декодируется с публичным ключом."""
        import jwt
        from django.conf import settings
        from apps.users.utils import encode_jwt
        user = User.objects.create_user(
            username='jwtdecode', password='pass12345'
        )
        token = encode_jwt(user)
        payload = jwt.decode(
            token, settings.JWT_PUBLIC_KEY, algorithms=['RS256']
        )
        self.assertEqual(payload['user_id'], user.id)
        self.assertEqual(payload['username'], user.username)
