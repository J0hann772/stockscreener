"""
Представления (views) для работы с тикерами.

Содержит views для просмотра, добавления (одиночного и массового)
и удаления тикеров. Все views требуют авторизации.
"""
import re

import httpx
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TickerForm
from .models import Ticker

MAX_TICKERS = 50
FASTAPI_URL = None  # будет браться из settings


def _validate_ticker_on_yahoo(symbol: str) -> bool:
    """
    Проверяет существование тикера через Yahoo Finance API.

    При сетевой ошибке (недоступен интернет, таймаут) возвращает True
    (fail-open), чтобы не блокировать пользователя из-за проблем сети.
    Только при явном ответе «тикер не найден» — возвращает False.

    Args:
        symbol (str): символ тикера (например, 'AAPL').

    Returns:
        bool: False только если Yahoo Finance явно ответил, что тикера нет.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    try:
        response = httpx.get(url, timeout=8, follow_redirects=True, headers=headers)
        if response.status_code != 200:
            # Сеть ответила, но не 200 — считаем тикер невалидным
            return False
        data = response.json()
        chart = data.get('chart', {})
        error = chart.get('error')
        result = chart.get('result')
        # Явная ошибка от Yahoo — тикер не существует
        if error is not None:
            return False
        return bool(result)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError):
        # Сеть недоступна — пропускаем тикер (fail-open)
        return True
    except Exception:
        # Любая другая ошибка (парсинг JSON и т.д.) — тоже пропускаем
        return True


@login_required
def ticker_list(request):
    """
    Показывает список тикеров и обрабатывает добавление нового (одиночного).

    GET — страница со списком и формой.
    POST — добавляет тикер, проверяет лимит 50 и валидность на Yahoo Finance.

    Args:
        request (HttpRequest): объект запроса Django.

    Returns:
        HttpResponse: страница со списком тикеров.
    """
    tickers = Ticker.objects.filter(user=request.user)

    if request.method == 'POST':
        form = TickerForm(request.POST)
        if form.is_valid():
            if tickers.count() >= MAX_TICKERS:
                return JsonResponse(
                    {'success': False, 'message': f'Достигнут лимит {MAX_TICKERS} тикеров'},
                    status=400
                )
            symbol = form.cleaned_data['symbol']
            if not _validate_ticker_on_yahoo(symbol):
                return JsonResponse(
                    {'success': False, 'message': f'Тикер «{symbol}» не найден. Добавление невозможно.'},
                    status=400
                )
            ticker = form.save(commit=False)
            ticker.user = request.user
            ticker.save()
            return JsonResponse({'success': True, 'message': f'Тикер {symbol} добавлен'})
        return JsonResponse({'success': False, 'message': 'Некорректный символ'}, status=400)

    form = TickerForm()
    return render(request, 'tickers/list.html', {'tickers': tickers, 'form': form})


@login_required
def add_bulk_tickers(request):
    """
    Обрабатывает массовое добавление тикеров из строки.

    Принимает строку тикеров, разбивает по любым не-латинским разделителям,
    валидирует каждый через Yahoo Finance и добавляет в базу.

    Args:
        request (HttpRequest): POST-запрос с полем 'tickers_raw'.

    Returns:
        JsonResponse: результат с добавленными, пропущенными и ошибочными тикерами.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не разрешён'}, status=405)

    raw = request.POST.get('tickers_raw', '')
    # Разбиваем по любому символу, не являющемуся латинской буквой или цифрой
    symbols = [s.upper() for s in re.split(r'[^A-Za-z0-9]+', raw) if s.strip()]
    # Убираем дубли, сохраняя порядок
    seen = set()
    unique_symbols = [s for s in symbols if not (s in seen or seen.add(s))]

    current_count = Ticker.objects.filter(user=request.user).count()
    added = []
    skipped_exists = []
    skipped_invalid = []
    skipped_limit = []

    for symbol in unique_symbols:
        if not symbol or len(symbol) > 15:
            skipped_invalid.append(symbol)
            continue

        if current_count >= MAX_TICKERS:
            skipped_limit.append(symbol)
            continue

        # Пропускаем уже существующие
        if Ticker.objects.filter(user=request.user, symbol=symbol).exists():
            skipped_exists.append(symbol)
            continue

        if not _validate_ticker_on_yahoo(symbol):
            skipped_invalid.append(symbol)
            continue

        Ticker.objects.create(user=request.user, symbol=symbol)
        added.append(symbol)
        current_count += 1

    return JsonResponse({
        'success': True,
        'added': added,
        'skipped_exists': skipped_exists,
        'skipped_invalid': skipped_invalid,
        'skipped_limit': skipped_limit,
        'message': f'Добавлено: {len(added)}, пропущено (нет на бирже): {len(skipped_invalid)}'
    })


@login_required
def delete_ticker(request, pk):
    """
    Удаляет тикер из списка пользователя.

    Args:
        request (HttpRequest): POST-запрос.
        pk (int): ID тикера.

    Returns:
        HttpResponse: редирект на список тикеров.
    """
    ticker = get_object_or_404(Ticker, pk=pk, user=request.user)
    if request.method == 'POST':
        ticker.delete()
    return redirect('ticker_list')


@login_required
def stocks_search(request):
    """
    Страница поиска акций по тикеру.
    GET без параметров — форма поиска.
    GET ?q=AAPL — ищет тикер и показывает базовую инфо (или ошибку).
    """
    query = request.GET.get('q', '').strip().upper()
    result = None
    error = None

    if query:
        fastapi_url = getattr(settings, 'FASTAPI_URL', 'http://fastapi:8001')
        try:
            resp = httpx.get(f'{fastapi_url}/stock-info/{query}', timeout=15.0)
            if resp.status_code == 200:
                result = resp.json()
            elif resp.status_code == 404:
                error = f'Тикер «{query}» не найден на бирже.'
            else:
                error = 'Ошибка при получении данных об акции.'
        except Exception as e:
            error = f'Ошибка соединения с сервером анализа: {e}'

    return render(request, 'tickers/stocks_search.html', {
        'query': query,
        'result': result,
        'error': error,
    })


@login_required
def stock_detail(request, symbol):
    """
    Детальная страница акции.
    Загружает инфо с FastAPI, рендерит страницу с графиком и данными.
    Стратегии пользователя передаются для прогона анализа.
    """
    symbol = symbol.upper()
    from apps.strategies.models import Strategy
    strategies = Strategy.objects.filter(user=request.user, is_active=True)

    return render(request, 'tickers/stock_detail.html', {
        'symbol': symbol,
        'strategies': strategies,
        'fastapi_url': getattr(settings, 'FASTAPI_URL', 'http://fastapi:8001'),
    })