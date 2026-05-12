"""
Представления для работы со стратегиями.

AJAX-based: создание и редактирование стратегий
происходит через JSON API, без Django FormSet.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Strategy, StrategyCondition


@login_required
def strategy_list(request):
    """
    Показывает список стратегий пользователя.

    Args:
        request (HttpRequest): объект запроса.

    Returns:
        HttpResponse: страница со списком стратегий.
    """
    strategies = Strategy.objects.filter(user=request.user).prefetch_related('conditions')
    return render(request, 'strategies/list.html', {'strategies': strategies})


@login_required
def strategy_create(request):
    """
    Страница создания новой стратегии.

    GET — пустая форма конструктора.
    POST — AJAX: сохраняет стратегию и все условия из JSON.

    Args:
        request (HttpRequest): объект запроса.

    Returns:
        HttpResponse/JsonResponse: страница или JSON с результатом.
    """
    if request.method == 'POST':
        return _save_strategy(request, strategy=None)
    return render(request, 'strategies/form.html', {'strategy': None, 'is_edit': False})


@login_required
def strategy_edit(request, pk):
    """
    Страница редактирования существующей стратегии.

    GET — форма с заполненными данными.
    POST — AJAX: обновляет стратегию и пересоздаёт условия.

    Args:
        request (HttpRequest): объект запроса.
        pk (int): ID стратегии.

    Returns:
        HttpResponse/JsonResponse: страница или JSON с результатом.
    """
    strategy = get_object_or_404(Strategy, pk=pk, user=request.user)
    if request.method == 'POST':
        return _save_strategy(request, strategy=strategy)

    conditions_data = list(strategy.conditions.values(
        'id', 'name', 'indicator', 'params', 'operator', 'value',
        'is_required', 'group_id', 'compare_to_indicator', 'compare_to_params'
    ))
    return render(request, 'strategies/form.html', {
        'strategy': strategy,
        'conditions_json': json.dumps(conditions_data),
        'is_edit': True,
    })


def _save_strategy(request, strategy):
    """
    Внутренняя функция сохранения стратегии из AJAX POST.

    Читает JSON из тела запроса, создаёт/обновляет Strategy
    и пересоздаёт все StrategyCondition.

    Args:
        request (HttpRequest): объект запроса с JSON в теле.
        strategy (Strategy | None): существующая стратегия или None для создания.

    Returns:
        JsonResponse: {'success': True, 'redirect': url} или {'success': False, 'error': msg}.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Некорректный JSON'}, status=400)

    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Название стратегии обязательно'}, status=400)

    if strategy is None:
        strategy = Strategy(user=request.user)

    strategy.name = name
    strategy.description = data.get('description', '')
    strategy.is_active = data.get('is_active', True)
    strategy.save()

    # Пересоздаём все условия
    strategy.conditions.all().delete()

    conditions = data.get('conditions', [])
    for cond in conditions:
        indicator = cond.get('indicator', '').strip().lower()
        if not indicator:
            continue
        StrategyCondition.objects.create(
            strategy=strategy,
            name=cond.get('name', ''),
            indicator=indicator,
            params=cond.get('params') or {},
            operator=cond.get('operator', '>'),
            value=cond.get('value'),
            is_required=cond.get('is_required', True),
            group_id=cond.get('group_id'),
            compare_to_indicator=cond.get('compare_to_indicator') or None,
            compare_to_params=cond.get('compare_to_params') or None,
        )

    return JsonResponse({'success': True, 'redirect': '/strategies/'})


@login_required
@require_POST
def strategy_delete(request, pk):
    """
    Удаляет стратегию пользователя.

    Args:
        request (HttpRequest): POST-запрос.
        pk (int): ID стратегии.

    Returns:
        HttpResponse: редирект на список стратегий.
    """
    strategy = get_object_or_404(Strategy, pk=pk, user=request.user)
    strategy.delete()
    return redirect('strategy_list')