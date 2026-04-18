"""
Представления (views) для работы с тикерами.

Содержит views для просмотра списка тикеров, добавления
нового тикера и удаления. Все views требуют авторизации.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Ticker
from .forms import TickerForm


@login_required
def ticker_list(request):
    """
    Показывает список тикеров пользователя и обрабатывает добавление нового.

    GET-запрос — показывает список тикеров и пустую форму.
    POST-запрос — добавляет новый тикер в список пользователя.

    Args:
        request (HttpRequest): объект запроса Django.

    Returns:
        HttpResponse: страница со списком тикеров и формой добавления.
    """
    tickers = Ticker.objects.filter(user=request.user)
    
    if request.method == 'POST':
        form = TickerForm(request.POST)
        if form.is_valid():
            ticker = form.save(commit=False)
            ticker.user = request.user
            ticker.save()
            return redirect('ticker_list')
    else:
        form = TickerForm()
        
    return render(request, 'tickers/list.html', {'tickers': tickers, 'form': form})


@login_required
def delete_ticker(request, pk):
    """
    Удаляет тикер из списка пользователя.

    Удалить можно только свой тикер. Удаление происходит
    только по POST-запросу.

    Args:
        request (HttpRequest): объект запроса Django.
        pk (int): ID тикера для удаления.

    Returns:
        HttpResponse: редирект на список тикеров.
    """
    ticker = get_object_or_404(Ticker, pk=pk, user=request.user)
    if request.method == 'POST':
        ticker.delete()
    return redirect('ticker_list')
