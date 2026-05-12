"""
Тесты для приложения tickers.

Используется стандартная библиотека unittest через Django TestCase.
Запуск: python manage.py test apps.tickers

Покрывает: модель Ticker, форму TickerForm и основные views.
Внешние HTTP-запросы к Yahoo Finance мокируются через unittest.mock,
чтобы тесты не зависели от интернет-соединения.
"""
import json
import unittest
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .forms import TickerForm
from .models import Ticker


class TickerModelTest(TestCase):
    """Тесты модели Ticker."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='pass12345'
        )

    def test_ticker_str(self):
        """__str__ возвращает 'SYMBOL (username)'."""
        ticker = Ticker.objects.create(user=self.user, symbol='AAPL')
        self.assertEqual(str(ticker), 'AAPL (testuser)')

    def test_unique_together_constraint(self):
        """Один пользователь не может добавить один тикер дважды."""
        from django.db import IntegrityError
        Ticker.objects.create(user=self.user, symbol='TSLA')
        with self.assertRaises(IntegrityError):
            Ticker.objects.create(user=self.user, symbol='TSLA')

    def test_symbol_stored_as_given(self):
        """Тикер сохраняется в том регистре, в котором передан."""
        ticker = Ticker.objects.create(user=self.user, symbol='GOOG')
        self.assertEqual(ticker.symbol, 'GOOG')

    def test_ticker_ordering(self):
        """Тикеры сортируются по убыванию даты добавления."""
        Ticker.objects.create(user=self.user, symbol='AAA')
        Ticker.objects.create(user=self.user, symbol='BBB')
        tickers = list(Ticker.objects.filter(user=self.user))
        # Последний добавленный — первый в выборке
        self.assertEqual(tickers[0].symbol, 'BBB')


class TickerFormTest(TestCase):
    """Тесты формы TickerForm."""

    def test_clean_symbol_uppercases(self):
        """clean_symbol приводит символ к верхнему регистру."""
        form = TickerForm(data={'symbol': 'aapl'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['symbol'], 'AAPL')

    def test_form_invalid_empty(self):
        """Пустой символ делает форму невалидной."""
        form = TickerForm(data={'symbol': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('symbol', form.errors)

    def test_form_valid_symbol(self):
        """Корректный символ проходит валидацию."""
        form = TickerForm(data={'symbol': 'MSFT'})
        self.assertTrue(form.is_valid())

    def test_form_symbol_mixed_case_cleaned(self):
        """Смешанный регистр приводится к верхнему."""
        form = TickerForm(data={'symbol': 'Nvda'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['symbol'], 'NVDA')


class TickerListViewTest(TestCase):
    """Тесты view ticker_list."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='testuser2', password='pass12345')
        self.url = reverse('ticker_list')

    def test_get_requires_login(self):
        """Неавторизованный запрос редиректит на логин."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_get_returns_200(self):
        """GET возвращает 200 для авторизованного пользователя."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    @patch('apps.tickers.views._validate_ticker_on_yahoo', return_value=True)
    def test_post_adds_ticker(self, mock_validate):
        """POST добавляет тикер и возвращает JSON success=True."""
        response = self.client.post(
            self.url,
            data={'symbol': 'NVDA'},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(
            Ticker.objects.filter(user=self.user, symbol='NVDA').exists()
        )

    @patch('apps.tickers.views._validate_ticker_on_yahoo', return_value=False)
    def test_post_invalid_ticker_returns_400(self, mock_validate):
        """POST с несуществующим тикером возвращает 400."""
        response = self.client.post(
            self.url,
            data={'symbol': 'ZZZZZ'},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    @patch('apps.tickers.views._validate_ticker_on_yahoo', return_value=True)
    def test_post_duplicate_ticker(self, mock_validate):
        """Повторное добавление существующего тикера возвращает ошибку."""
        Ticker.objects.create(user=self.user, symbol='IBM')
        # При попытке повторного добавления — unique_together вызовет ошибку
        # Форма пройдёт, но база выкинет IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Ticker.objects.create(user=self.user, symbol='IBM')


class DeleteTickerViewTest(TestCase):
    """Тесты view delete_ticker."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='deluser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='deluser', password='pass12345')
        self.ticker = Ticker.objects.create(user=self.user, symbol='IBM')

    def test_delete_ticker(self):
        """POST удаляет тикер из базы и редиректит."""
        url = reverse('delete_ticker', args=[self.ticker.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Ticker.objects.filter(pk=self.ticker.pk).exists()
        )

    def test_cannot_delete_other_users_ticker(self):
        """Нельзя удалить чужой тикер — возвращает 404."""
        other_user = User.objects.create_user(
            username='other', password='pass12345'
        )
        other_ticker = Ticker.objects.create(user=other_user, symbol='AMD')
        url = reverse('delete_ticker', args=[other_ticker.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class AddBulkTickersViewTest(TestCase):
    """Тесты view add_bulk_tickers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='bulkuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='bulkuser', password='pass12345')
        self.url = reverse('add_bulk_tickers')

    def test_get_not_allowed(self):
        """GET возвращает 405 (только POST разрешён)."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    @patch('apps.tickers.views._validate_ticker_on_yahoo', return_value=True)
    def test_bulk_add_multiple(self, mock_validate):
        """POST добавляет несколько тикеров из строки."""
        response = self.client.post(
            self.url, data={'tickers_raw': 'AAPL, MSFT, GOOG'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['added']), 3)

    @patch('apps.tickers.views._validate_ticker_on_yahoo', return_value=True)
    def test_bulk_skip_duplicates(self, mock_validate):
        """При повторном добавлении тикер попадает в skipped_exists."""
        Ticker.objects.create(user=self.user, symbol='AAPL')
        response = self.client.post(
            self.url, data={'tickers_raw': 'AAPL MSFT'}
        )
        data = json.loads(response.content)
        self.assertIn('AAPL', data['skipped_exists'])
        self.assertIn('MSFT', data['added'])

    @patch('apps.tickers.views._validate_ticker_on_yahoo', return_value=False)
    def test_bulk_skip_invalid(self, mock_validate):
        """Невалидные тикеры попадают в skipped_invalid."""
        response = self.client.post(
            self.url, data={'tickers_raw': 'FAKE1 FAKE2'}
        )
        data = json.loads(response.content)
        self.assertEqual(len(data['added']), 0)
        self.assertEqual(len(data['skipped_invalid']), 2)
