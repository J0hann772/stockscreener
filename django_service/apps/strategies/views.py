"""
Представления (views) для работы со стратегиями.

Содержит views для просмотра списка стратегий, создания новой
стратегии с условиями и удаления стратегии. Все views требуют авторизации.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Strategy
from .forms import StrategyForm, StrategyConditionFormSet


@login_required
def strategy_list(request):
    """
    Показывает список стратегий текущего пользователя.

    Args:
        request (HttpRequest): объект запроса Django.

    Returns:
        HttpResponse: страница со списком стратегий.
    """
    strategies = Strategy.objects.filter(user=request.user)
    return render(request, 'strategies/list.html', {'strategies': strategies})


@login_required
def strategy_create(request):
    """
    Создаёт новую стратегию с условиями.

    GET-запрос — показывает пустую форму стратегии и formset условий.
    POST-запрос — сохраняет стратегию и её условия в базу данных.

    Args:
        request (HttpRequest): объект запроса Django.

    Returns:
        HttpResponse: редирект на список стратегий при успехе,
            либо страница с формой создания.
    """
    if request.method == 'POST':
        form = StrategyForm(request.POST)
        if form.is_valid():
            strategy = form.save(commit=False)
            strategy.user = request.user
            formset = StrategyConditionFormSet(request.POST, instance=strategy)
            
            if formset.is_valid():
                strategy.save()
                formset.save()
                return redirect('strategy_list')
    else:
        form = StrategyForm()
        formset = StrategyConditionFormSet()
        
    return render(request, 'strategies/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Создать стратегию'
    })


@login_required
def strategy_delete(request, pk):
    """
    Удаляет стратегию по её ID.

    Удалить можно только свою стратегию. Удаление происходит
    только по POST-запросу.

    Args:
        request (HttpRequest): объект запроса Django.
        pk (int): ID стратегии для удаления.

    Returns:
        HttpResponse: редирект на список стратегий.
    """
    strategy = get_object_or_404(Strategy, pk=pk, user=request.user)
    if request.method == 'POST':
        strategy.delete()
    return redirect('strategy_list')
