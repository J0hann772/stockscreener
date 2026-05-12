"""
Тесты для приложения analysis.

Используется стандартная библиотека unittest через Django TestCase.
Запуск: python manage.py test apps.analysis

Покрывает: модель AnalysisRun, view-функции запуска и истории анализа.
"""
import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.strategies.models import Strategy
from apps.tickers.models import Ticker
from .models import AnalysisRun


class AnalysisRunModelTest(TestCase):
    """Тесты модели AnalysisRun."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='analuser', password='pass12345'
        )
        self.strategy = Strategy.objects.create(
            user=self.user, name='Стратегия анализа'
        )

    def test_analysis_run_str(self):
        """__str__ содержит имя пользователя и название стратегии."""
        run = AnalysisRun.objects.create(
            user=self.user,
            strategy=self.strategy,
            strategy_name='Стратегия анализа',
            tickers_analyzed=5,
            tickers_matched=2,
        )
        result = str(run)
        self.assertIn('analuser', result)
        self.assertIn('Стратегия анализа', result)

    def test_default_matched_tickers_empty(self):
        """По умолчанию matched_tickers — пустой список."""
        run = AnalysisRun.objects.create(
            user=self.user,
            strategy_name='Пустой запуск',
        )
        self.assertEqual(run.matched_tickers, [])

    def test_default_details_empty(self):
        """По умолчанию details — пустой список."""
        run = AnalysisRun.objects.create(
            user=self.user,
            strategy_name='Пустой запуск 2',
        )
        self.assertEqual(run.details, [])

    def test_strategy_fk_set_null_on_delete(self):
        """При удалении Strategy поле strategy в AnalysisRun обнуляется."""
        run = AnalysisRun.objects.create(
            user=self.user,
            strategy=self.strategy,
            strategy_name='Тест удаления',
        )
        self.strategy.delete()
        run.refresh_from_db()
        self.assertIsNone(run.strategy)

    def test_error_field_default_blank(self):
        """Поле error пустое по умолчанию."""
        run = AnalysisRun.objects.create(
            user=self.user,
            strategy_name='Без ошибок',
        )
        self.assertEqual(run.error, '')

    def test_tickers_counters_saved_correctly(self):
        """Счётчики tickers_analyzed и tickers_matched сохраняются корректно."""
        run = AnalysisRun.objects.create(
            user=self.user,
            strategy_name='Счётчики',
            tickers_analyzed=10,
            tickers_matched=3,
            matched_tickers=['AAPL', 'TSLA', 'GOOG'],
        )
        self.assertEqual(run.tickers_analyzed, 10)
        self.assertEqual(run.tickers_matched, 3)
        self.assertEqual(len(run.matched_tickers), 3)

    def test_matched_tickers_json_field(self):
        """matched_tickers корректно сохраняет список строк."""
        tickers = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META']
        run = AnalysisRun.objects.create(
            user=self.user,
            strategy_name='JSON тест',
            matched_tickers=tickers,
        )
        run.refresh_from_db()
        self.assertEqual(run.matched_tickers, tickers)

    def test_details_json_field(self):
        """details корректно сохраняет список словарей."""
        details = [
            {'ticker': 'AAPL', 'matched': True},
            {'ticker': 'TSLA', 'matched': False},
        ]
        run = AnalysisRun.objects.create(
            user=self.user,
            strategy_name='Details тест',
            details=details,
        )
        run.refresh_from_db()
        self.assertEqual(run.details, details)

    def test_user_cascade_delete(self):
        """При удалении пользователя все его AnalysisRun удаляются."""
        run_id = AnalysisRun.objects.create(
            user=self.user,
            strategy_name='Каскад',
        ).pk
        self.user.delete()
        self.assertFalse(AnalysisRun.objects.filter(pk=run_id).exists())


class ChartsViewTest(TestCase):
    """Тесты view charts_view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='chartsuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='chartsuser', password='pass12345')
        self.url = reverse('analysis_charts')

    def test_get_returns_200(self):
        """GET возвращает страницу графиков."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_requires_login(self):
        """Неавторизованный запрос редиректит на логин."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_with_tickers_param(self):
        """GET с параметром ?tickers= возвращает 200."""
        response = self.client.get(self.url + '?tickers=AAPL,MSFT')
        self.assertEqual(response.status_code, 200)


class RunAnalysisViewTest(TestCase):
    """Тесты view run_analysis."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='runuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='runuser', password='pass12345')
        self.url = reverse('analysis_run')

    def test_get_returns_200(self):
        """GET возвращает страницу запуска анализа."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_requires_login(self):
        """Неавторизованный запрос редиректит на логин."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class ClearHistoryViewTest(TestCase):
    """Тесты view clear_history."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='clearuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='clearuser', password='pass12345')
        self.url = reverse('analysis_clear_history')

    def test_post_clears_history(self):
        """POST удаляет всю историю пользователя."""
        AnalysisRun.objects.create(
            user=self.user, strategy_name='Запуск 1'
        )
        AnalysisRun.objects.create(
            user=self.user, strategy_name='Запуск 2'
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['deleted'], 2)
        self.assertEqual(
            AnalysisRun.objects.filter(user=self.user).count(), 0
        )

    def test_get_not_allowed(self):
        """GET возвращает 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_does_not_clear_other_users_history(self):
        """POST не затрагивает историю других пользователей."""
        other_user = User.objects.create_user(
            username='otheruser', password='pass12345'
        )
        AnalysisRun.objects.create(
            user=other_user, strategy_name='Чужой запуск'
        )
        self.client.post(self.url)
        self.assertEqual(
            AnalysisRun.objects.filter(user=other_user).count(), 1
        )


class DeleteRunViewTest(TestCase):
    """Тесты view delete_run."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='deleterunuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='deleterunuser', password='pass12345')
        self.run = AnalysisRun.objects.create(
            user=self.user, strategy_name='Удалить'
        )

    def test_post_deletes_run(self):
        """POST удаляет одну запись истории."""
        url = reverse('analysis_delete_run', args=[self.run.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(
            AnalysisRun.objects.filter(pk=self.run.pk).exists()
        )

    def test_cannot_delete_other_users_run(self):
        """Нельзя удалить чужую запись — возвращает 404."""
        other_user = User.objects.create_user(
            username='other3', password='pass12345'
        )
        other_run = AnalysisRun.objects.create(
            user=other_user, strategy_name='Чужой'
        )
        url = reverse('analysis_delete_run', args=[other_run.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class ApiRunAnalysisViewTest(TestCase):
    """Тесты view api_run_analysis."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='apirunuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='apirunuser', password='pass12345')
        self.strategy = Strategy.objects.create(
            user=self.user, name='API Стратегия'
        )
        self.url = reverse('analysis_api_run')

    def test_missing_strategy_id_returns_400(self):
        """POST без strategy_id возвращает 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_invalid_json_returns_400(self):
        """POST с невалидным JSON возвращает 400."""
        response = self.client.post(
            self.url,
            data='not-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_no_tickers_returns_400(self):
        """POST без тикеров у пользователя возвращает 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({'strategy_id': self.strategy.pk}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('тикер', data['error'].lower())

    @patch('apps.analysis.views.httpx.post')
    def test_fastapi_error_returns_502(self, mock_post):
        """При ошибке подключения к FastAPI возвращает 502."""
        import httpx
        mock_post.side_effect = httpx.ConnectError('connection refused')
        Ticker.objects.create(user=self.user, symbol='AAPL')
        response = self.client.post(
            self.url,
            data=json.dumps({'strategy_id': self.strategy.pk}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 502)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    @patch('apps.analysis.views.httpx.post')
    def test_successful_run_returns_task_id(self, mock_post):
        """При успешном запросе к FastAPI возвращает task_id."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'task_id': 'abc-123'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        Ticker.objects.create(user=self.user, symbol='AAPL')
        response = self.client.post(
            self.url,
            data=json.dumps({'strategy_id': self.strategy.pk}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['task_id'], 'abc-123')
