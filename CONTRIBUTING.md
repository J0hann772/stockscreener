# Contributing to MarketView

## Ветки

Основная ветка разработки — `dev`. Каждый участник работает в своей ветке и сливает в `dev`.

**Два типа веток в проекте:**

| Тип | Примеры |
|---|---|
| Личная (по имени) | `eugen`, `front_sonya`, `polina_tests`, `polina_cash` |
| По функционалу | `Indicators`, `analysis_endpoint`, `register/login`, `requirejwt`, `polina_fastapi_auth`, `polina_service_tests` |

```bash
# Создать ветку от dev
git checkout dev
git pull origin dev
git checkout -b my_feature

# Слить обратно в dev
git checkout dev
git merge my_feature
git push origin dev
```

## Коммиты

Пишите понятно что сделали — на русском или английском, в произвольном стиле. Главное — однозначно описать изменение.

**Примеры коммитов из проекта:**
```
скруглил все кнопки
fix обновления профиля после входа ошибка сохранения в несуществующий профиль
fix documentation
Test for Indicators
auth_tests_need_to_check
пофиксил баг с подгрузкой static, добавил view функции для run_analysis, index(дашборд)
Добавил docstring в начале файла
+ аннотация
+public_key
```

## Что не коммитить

- `.env` и ключи (`keys/`, `*.pem`)
- `__pycache__/`, `.idea/`, `.venv/`
- Лог-файлы (`*.log`, `logs/*`)

## Команда

Буряк С.В., Салтанова С.А., Гавришов Е.А., Агапченко Н.Н., Гурская В.В.,
Новикова М.А., Ларионова П.Г., Симонов В.М., Азизов М.К.
