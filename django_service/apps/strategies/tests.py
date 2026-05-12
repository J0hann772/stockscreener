"""
Тесты для приложения strategies.

Используется стандартная библиотека unittest через Django TestCase.
Запуск: python manage.py test apps.strategies

Покрывает: модели Strategy и StrategyCondition, метод to_fastapi_config,
а также view-функции создания, редактирования и удаления стратегий.
"""
import json
import unittest

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.strategies.models import Strategy, StrategyCondition


class StrategyFormTest(TestCase):
    """Тесты формы StrategyForm из strategies/forms.py."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='formuser', password='pass12345'
        )

    def test_valid_form(self):
        """Корректные данные делают форму валидной."""
        from apps.strategies.forms import StrategyForm
        form = StrategyForm(data={
            'name': 'Тестовая стратегия',
            'description': 'Описание',
            'is_active': True,
        })
        self.assertTrue(form.is_valid())

    def test_missing_name_invalid(self):
        """Без названия форма невалидна."""
        from apps.strategies.forms import StrategyForm
        form = StrategyForm(data={
            'name': '',
            'description': '',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_description_optional(self):
        """Описание необязательно."""
        from apps.strategies.forms import StrategyForm
        form = StrategyForm(data={
            'name': 'Без описания',
            'is_active': True,
        })
        self.assertTrue(form.is_valid())


class StrategyConditionFormTest(TestCase):
    """Тесты формы StrategyConditionForm."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='condformuser', password='pass12345'
        )

    def test_valid_condition_form(self):
        """Корректные данные для условия."""
        from apps.strategies.forms import StrategyConditionForm
        form = StrategyConditionForm(data={
            'indicator': 'rsi',
            'operator': '>',
            'value': 30,
        })
        self.assertTrue(form.is_valid())

    def test_missing_indicator_invalid(self):
        """Без индикатора форма невалидна."""
        from apps.strategies.forms import StrategyConditionForm
        form = StrategyConditionForm(data={
            'indicator': '',
            'operator': '>',
            'value': 30,
        })
        self.assertFalse(form.is_valid())


class StrategyModelTest(TestCase):
    """Тесты модели Strategy."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='stratuser', password='pass12345'
        )

    def test_strategy_str(self):
        """__str__ возвращает 'название (пользователь)'."""
        strategy = Strategy.objects.create(
            user=self.user, name='Тестовая стратегия'
        )
        self.assertEqual(str(strategy), 'Тестовая стратегия (stratuser)')

    def test_strategy_default_is_active(self):
        """Стратегия активна по умолчанию."""
        strategy = Strategy.objects.create(user=self.user, name='Активная')
        self.assertTrue(strategy.is_active)

    def test_strategy_description_default_blank(self):
        """Описание по умолчанию пустое."""
        strategy = Strategy.objects.create(user=self.user, name='Без описания')
        self.assertEqual(strategy.description, '')

    def test_to_fastapi_config_required_condition(self):
        """to_fastapi_config помещает is_required=True в required_conditions."""
        strategy = Strategy.objects.create(user=self.user, name='Config-тест')
        StrategyCondition.objects.create(
            strategy=strategy,
            indicator='rsi',
            operator='>',
            value=30,
            is_required=True,
        )
        config = strategy.to_fastapi_config()
        self.assertEqual(len(config['required_conditions']), 1)
        self.assertEqual(len(config['optional_groups']), 0)
        self.assertEqual(config['required_conditions'][0]['indicator'], 'rsi')

    def test_to_fastapi_config_optional_condition(self):
        """to_fastapi_config помещает is_required=False в optional_groups."""
        strategy = Strategy.objects.create(user=self.user, name='Optional-тест')
        StrategyCondition.objects.create(
            strategy=strategy,
            indicator='ema',
            operator='>',
            value=50,
            is_required=False,
            group_id=1,
        )
        config = strategy.to_fastapi_config()
        self.assertEqual(len(config['required_conditions']), 0)
        self.assertEqual(len(config['optional_groups']), 1)

    def test_to_fastapi_config_empty(self):
        """Стратегия без условий возвращает пустые списки."""
        strategy = Strategy.objects.create(user=self.user, name='Пустая')
        config = strategy.to_fastapi_config()
        self.assertEqual(config['required_conditions'], [])
        self.assertEqual(config['optional_groups'], [])

    def test_to_fastapi_config_mixed_conditions(self):
        """Условия разных типов распределяются корректно."""
        strategy = Strategy.objects.create(user=self.user, name='Смешанная')
        StrategyCondition.objects.create(
            strategy=strategy, indicator='rsi', operator='>', value=30,
            is_required=True,
        )
        StrategyCondition.objects.create(
            strategy=strategy, indicator='ema', operator='<', value=200,
            is_required=False, group_id=1,
        )
        config = strategy.to_fastapi_config()
        self.assertEqual(len(config['required_conditions']), 1)
        self.assertEqual(len(config['optional_groups']), 1)


class StrategyConditionModelTest(TestCase):
    """Тесты модели StrategyCondition."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='conduser', password='pass12345'
        )
        self.strategy = Strategy.objects.create(
            user=self.user, name='Стратегия'
        )

    def test_condition_str_with_value(self):
        """__str__ содержит индикатор и оператор."""
        cond = StrategyCondition.objects.create(
            strategy=self.strategy,
            indicator='rsi',
            operator='>',
            value=70,
        )
        result = str(cond)
        self.assertIn('rsi', result)
        self.assertIn('>', result)

    def test_condition_str_cross_indicator(self):
        """__str__ при кросс-индикаторном сравнении содержит 'vs'."""
        cond = StrategyCondition.objects.create(
            strategy=self.strategy,
            indicator='ema',
            operator='cross_up',
            compare_to_indicator='sma',
        )
        self.assertIn('vs', str(cond))

    def test_condition_default_is_required(self):
        """По умолчанию условие обязательное (is_required=True)."""
        cond = StrategyCondition.objects.create(
            strategy=self.strategy,
            indicator='macd',
            operator='>',
            value=0,
        )
        self.assertTrue(cond.is_required)


class StrategyCreateViewTest(TestCase):
    """Тесты view strategy_create."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='createuser', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='createuser', password='pass12345')
        self.url = reverse('strategy_create')

    def test_get_returns_200(self):
        """GET возвращает страницу формы."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_creates_strategy(self):
        """POST с корректным JSON создаёт стратегию."""
        payload = {
            'name': 'Новая стратегия',
            'description': 'Описание',
            'is_active': True,
            'conditions': [
                {
                    'indicator': 'rsi',
                    'operator': '>',
                    'value': 30,
                    'is_required': True,
                    'params': {'period': 14},
                }
            ],
        }
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(
            Strategy.objects.filter(
                user=self.user, name='Новая стратегия'
            ).exists()
        )

    def test_post_missing_name_returns_400(self):
        """POST без названия возвращает 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({'name': '', 'conditions': []}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_post_invalid_json_returns_400(self):
        """POST с невалидным JSON возвращает 400."""
        response = self.client.post(
            self.url,
            data='not-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_post_requires_login(self):
        """Неавторизованный пользователь получает редирект."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class StrategyDeleteViewTest(TestCase):
    """Тесты view strategy_delete."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='delstrat', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='delstrat', password='pass12345')
        self.strategy = Strategy.objects.create(
            user=self.user, name='Удалить меня'
        )

    def test_delete_strategy(self):
        """POST удаляет стратегию и редиректит."""
        url = reverse('strategy_delete', args=[self.strategy.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Strategy.objects.filter(pk=self.strategy.pk).exists()
        )

    def test_cannot_delete_other_users_strategy(self):
        """Нельзя удалить чужую стратегию — возвращает 404."""
        other_user = User.objects.create_user(
            username='other2', password='pass12345'
        )
        other_strategy = Strategy.objects.create(
            user=other_user, name='Чужая'
        )
        url = reverse('strategy_delete', args=[other_strategy.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class StrategyEditViewTest(TestCase):
    """Тесты view strategy_edit."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='editstrat', password='pass12345'
        )
        self.client = Client()
        self.client.login(username='editstrat', password='pass12345')
        self.strategy = Strategy.objects.create(
            user=self.user, name='Старое название'
        )

    def test_get_returns_200(self):
        """GET возвращает форму редактирования."""
        url = reverse('strategy_edit', args=[self.strategy.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_post_updates_strategy(self):
        """POST обновляет название стратегии."""
        url = reverse('strategy_edit', args=[self.strategy.pk])
        payload = {
            'name': 'Новое название',
            'description': '',
            'is_active': True,
            'conditions': [],
        }
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.strategy.refresh_from_db()
        self.assertEqual(self.strategy.name, 'Новое название')
