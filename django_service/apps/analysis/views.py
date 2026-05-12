"""
Представления для запуска анализа и просмотра истории.

Сквозной путь: Django → FastAPI → результаты → сохранение в БД.
"""
import httpx
import logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.strategies.models import Strategy
from apps.tickers.models import Ticker
from django.views.decorators.clickjacking import xframe_options_exempt
from .models import AnalysisRun

logger = logging.getLogger('apps.analysis')


@login_required
def charts_view(request):
    """
    Страница просмотра графиков.
    Данные сериализуются для JS, который управляет отображением, пагинацией
    и подгрузкой данных (через Lightweight Charts).
    Принимает GET-параметр ?tickers=AAPL,NVDA для предзаполнения тикеров из истории.
    """
    profile_tickers = list(request.user.tickers.values_list('symbol', flat=True))
    analyses = AnalysisRun.objects.filter(
        user=request.user, tickers_matched__gt=0
    ).order_by('-created_at')[:15]

    # Предзаполненные тикеры из query-параметра (из истории анализа)
    preload_tickers_param = request.GET.get('tickers', '')
    preload_tickers = [t.strip().upper() for t in preload_tickers_param.split(',') if t.strip()]

    return render(request, 'analysis/charts.html', {
        'profile_tickers': profile_tickers,
        'analyses': analyses,
        'preload_tickers': preload_tickers,
    })

@login_required
def run_analysis(request):
    """
    Страница запуска анализа и просмотра истории.

    GET — рендерит страницу с двумя вкладками:
        · «Запустить» — выбор стратегии и кнопка запуска.
        · «История» — список прошлых запусков с возможностью очистки.

    Args:
        request (HttpRequest): HTTP-запрос.

    Returns:
        HttpResponse: HTML-страница.
    """
    strategies = Strategy.objects.filter(user=request.user, is_active=True)
    history = AnalysisRun.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(request, 'analysis/run.html', {
        'strategies': strategies,
        'history': history,
    })


@login_required
@require_POST
def api_run_analysis(request):
    """
    AJAX-endpoint запуска анализа.

    Читает strategy_id из тела запроса, формирует конфиг стратегии,
    получает тикеры пользователя и отправляет запрос в FastAPI.
    Результат сохраняется в AnalysisRun и возвращается клиенту.

    Args:
        request (HttpRequest): POST-запрос с JSON-телом {'strategy_id': int}.

    Returns:
        JsonResponse: результаты анализа или сообщение об ошибке.
    """
    import json
    try:
        body = json.loads(request.body)
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Некорректный запрос'}, status=400)

    strategy_id = body.get('strategy_id')
    if not strategy_id:
        return JsonResponse({'success': False, 'error': 'Не указана стратегия'}, status=400)

    strategy = get_object_or_404(Strategy, pk=strategy_id, user=request.user)

    # Получаем тикеры пользователя
    tickers = list(
        Ticker.objects.filter(user=request.user).values_list('symbol', flat=True)
    )
    if not tickers:
        return JsonResponse({'success': False, 'error': 'У вас нет тикеров для анализа'}, status=400)

    # Формируем конфиг стратегии
    strategy_config = strategy.to_fastapi_config()

    # Отправляем запрос в FastAPI
    fastapi_url = getattr(settings, 'FASTAPI_URL', 'http://fastapi:8001')
    internal_key = getattr(settings, 'INTERNAL_API_KEY', '')

    try:
        response = httpx.post(
            f'{fastapi_url}/analyze/',
            json={'tickers': tickers, 'strategy_config': strategy_config},
            headers={'X-Internal-Key': internal_key},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Анализ поставлен в очередь: user=%s, strategy=%s, tickers=%d, task_id=%s",
                    request.user.username, strategy.name, len(tickers), data.get('task_id'))
    except Exception as e:
        logger.error("Ошибка подключения к FastAPI: user=%s, error=%s", request.user.username, e)
        return JsonResponse({'success': False, 'error': f'Ошибка подключения к бэкенду анализа: {str(e)}'}, status=502)

    return JsonResponse({'success': True, 'task_id': data.get('task_id'), 'strategy_id': strategy_id})


@login_required
@require_POST
def api_status_analysis(request):
    import json
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid payload'}, status=400)
        
    task_id = body.get('task_id')
    strategy_id = body.get('strategy_id')
    if not task_id or not strategy_id:
        return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)

    fastapi_url = getattr(settings, 'FASTAPI_URL', 'http://fastapi:8001')
    internal_key = getattr(settings, 'INTERNAL_API_KEY', '')

    try:
        resp = httpx.get(
            f'{fastapi_url}/analyze/status/{task_id}',
            headers={'X-Internal-Key': internal_key},
            timeout=5.0
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка поллинга статуса: {str(e)}'}, status=502)

    if data.get('status') == 'pending':
        return JsonResponse({'success': True, 'status': 'pending'})

    if data.get('status') == 'failed':
        return JsonResponse({'success': False, 'error': data.get('error', 'Task failed')})

    # Успех
    result = data.get('result', {})
    matched = result.get('matched', [])
    details = result.get('details', [])

    strategy = get_object_or_404(Strategy, pk=strategy_id, user=request.user)
    tickers_count = len(details)

    # Сохраняем историю
    run = AnalysisRun.objects.create(
        user=request.user,
        strategy=strategy,
        strategy_name=strategy.name,
        tickers_analyzed=tickers_count,
        tickers_matched=len(matched),
        matched_tickers=matched,
        details=details,
    )
    logger.info("Результат анализа сохранён: user=%s run_id=%d, прошло %d/%d",
                request.user.username, run.id, len(matched), tickers_count)

    return JsonResponse({
        'success': True,
        'status': 'completed',
        'run_id': run.id,
        'strategy_name': strategy.name,
        'tickers_analyzed': tickers_count,
        'tickers_matched': len(matched),
        'matched': matched,
        'details': details,
    })


@login_required
@require_POST
def clear_history(request):
    """
    Очищает всю историю анализов пользователя.

    Args:
        request (HttpRequest): POST-запрос.

    Returns:
        JsonResponse: {'success': True, 'deleted': N}.
    """
    deleted, _ = AnalysisRun.objects.filter(user=request.user).delete()
    return JsonResponse({'success': True, 'deleted': deleted})


@login_required
@require_POST
def delete_run(request, pk):
    """
    Удаляет одну запись истории анализа.

    Args:
        request (HttpRequest): POST-запрос.
        pk (int): ID записи.

    Returns:
        JsonResponse: {'success': True}.
    """
    run = get_object_or_404(AnalysisRun, pk=pk, user=request.user)
    run.delete()
    return JsonResponse({'success': True})


@login_required
@require_POST
def api_analyze_single(request):
    """
    AJAX-endpoint анализа одного тикера через выбранную стратегию.
    Используется на странице детальной информации об акции.

    Args:
        request (HttpRequest): POST-запрос с JSON {'ticker': str, 'strategy_id': int}.

    Returns:
        JsonResponse: результаты анализа одного тикера.
    """
    import json
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Некорректный запрос'}, status=400)

    ticker = body.get('ticker', '').strip().upper()
    strategy_id = body.get('strategy_id')

    if not ticker or not strategy_id:
        return JsonResponse({'success': False, 'error': 'Не указан тикер или стратегия'}, status=400)

    strategy = get_object_or_404(Strategy, pk=strategy_id, user=request.user)
    strategy_config = strategy.to_fastapi_config()

    fastapi_url = getattr(settings, 'FASTAPI_URL', 'http://fastapi:8001')
    internal_key = getattr(settings, 'INTERNAL_API_KEY', '')

    try:
        resp = httpx.post(
            f'{fastapi_url}/analyze-one/',
            json={'ticker': ticker, 'strategy_config': strategy_config},
            headers={'X-Internal-Key': internal_key},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка анализа: {str(e)}'}, status=502)

    return JsonResponse({
        'success': True,
        'strategy_name': strategy.name,
        'matched': data.get('matched', []),
        'details': data.get('details', []),
    })