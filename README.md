# Аналитическая платформа для акций (Django + FastAPI)

## Описание архитектуры

Проект построен на базе микросервисной архитектуры:

- **Django (Основной бэкенд)** — управление пользователями, тикерами, стратегиями и анализом.
- **FastAPI (Сервис аналитики)** — высокопроизводительный асинхронный микросервис для анализа акций и получения рыночных данных.
- **Celery + Redis** — очередь фоновых задач. Анализ выполняется асинхронно, не блокируя интерфейс.
- **PostgreSQL** — основная реляционная база данных.
- **Redis** — брокер задач Celery + хранилище результатов.

---

## Возможности платформы

| Раздел        | Описание |
|---------------|----------|
| **Главная**   | Введение в платформу, переход к созданию стратегий |
| **Акции**     | Поиск любой акции по тикеру. Детальная страница с полноэкранным графиком (Lightweight Charts), техническими индикаторами (SMA, EMA, RSI, MACD, Объём) и всей информацией об акции на русском языке. Прогон через свои стратегии прямо со страницы |
| **Мои тикеры** | Список акций пользователя, добавление одиночное/массовое, валидация через Yahoo Finance |
| **Стратегии** | Создание торговых стратегий с условиями (AND/OR), индикаторы RSI, EMA, SMA, MACD, Stochastic и др. |
| **Анализ**    | Запуск анализа тикеров по стратегии через Celery. История запусков с кнопкой перехода на графики прошедших акций |
| **Графики**   | Свечные графики для всех тикеров из профиля или из результата анализа |

---

## Структура проекта

```
stockscreener/
├── django_service/         # Django-приложение
│   ├── apps/
│   │   ├── analysis/       # Запуск анализа, история
│   │   ├── strategies/     # Управление стратегиями
│   │   ├── tickers/        # Тикеры + страница Акции
│   │   └── users/          # Авторизация и профиль
│   ├── templates/          # HTML-шаблоны
│   └── keys/               # RSA ключи (авто-генерируются)
├── fastapi_service/        # FastAPI-микросервис
│   ├── auth/               # Проверка JWT и internal key
│   ├── indicators/         # RSI, MACD, EMA, Stochastic и др.
│   ├── schemas/            # Движок анализа стратегий
│   └── keys/               # RSA ключи (авто-генерируются)
├── .env                    # Единый файл переменных окружения
├── generate_keys.py        # Скрипт генерации RSA ключей
├── docker-compose.yml
└── docker-compose.override.yml  # Dev-режим (hot reload)
```

---

## Быстрый старт

### 1. Настройка переменных окружения

Создайте единственный файл `.env` в корне проекта:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True

DB_NAME=my_db
DB_USER=db_user
DB_PASSWORD=your_password
DB_HOST=postgres
DB_PORT=5432

REDIS_URL=redis://redis:6379/0
INTERNAL_API_KEY=your-internal-key-here
FASTAPI_URL=http://fastapi:8001
```

### 2. RSA ключи (JWT-аутентификация)

Ключи **генерируются автоматически** при первом запуске:
- В Docker: сервис `init_keys` создаёт ключи в shared volume до запуска Django и FastAPI.
- Локально: Django и FastAPI сами запускают `generate_keys.py` при отсутствии ключей.

Для ручной генерации:
```bash
python generate_keys.py
```

### 3. Запуск

```bash
# Dev-режим (с hot reload, монтированием кода)
docker compose up --build

# Продакшн-режим (без override)
docker compose -f docker-compose.yml up --build
```

### 4. Инициализация БД (первый запуск)

```bash
docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser
```

---

## Доступные URL

| Адрес | Описание |
|-------|----------|
| http://localhost:8000 | Главная страница |
| http://localhost:8000/tickers/stocks/ | Поиск акций |
| http://localhost:8000/tickers/stocks/AAPL/ | Страница акции AAPL |
| http://localhost:8000/tickers/ | Мои тикеры |
| http://localhost:8000/strategies/ | Стратегии |
| http://localhost:8000/analysis/run/ | Запуск анализа / история |
| http://localhost:8000/analysis/charts/ | Графики |
| http://localhost:8000/admin/ | Панель администратора |
| http://localhost:8001/docs | FastAPI Swagger UI |
| http://localhost:8001/stock-info/{ticker} | Инфо об акции (FastAPI) |
| http://localhost:8001/chart-data/{ticker} | OHLCV данные (FastAPI) |

---

## FastAPI эндпоинты

| Метод | URL | Авторизация | Описание |
|-------|-----|-------------|----------|
| `POST` | `/analyze/` | Internal Key | Постановка задачи анализа в очередь Celery |
| `GET` | `/analyze/status/{task_id}` | Internal Key | Статус задачи Celery |
| `POST` | `/analyze-one/` | Internal Key | Анализ одного тикера по стратегии (страница акции) |
| `GET` | `/chart-data/{ticker}` | Открытый | OHLCV свечи для графика |
| `GET` | `/stock-info/{ticker}` | Открытый | Полная информация об акции |

---

## Подключение к БД из IDE

PostgreSQL доступен на порту `5434` хост-машины:

| Параметр | Значение |
|----------|----------|
| Host     | localhost |
| Port     | 5434 |
| User     | db_user |
| Password | (из .env) |
| Database | my_db |

---

## Управление контейнерами

```bash
# Остановка с сохранением данных
docker compose down

# Полный сброс данных (БД, ключи)
docker compose down -v

# Пересборка одного сервиса
docker compose up -d --build django
docker compose up -d --build fastapi
```

---

## Персистентность данных

- **PostgreSQL** — volume `postgres_data`. Данные сохраняются между перезапусками.
- **Redis** — volume `redis_data` с AOF (`--appendonly yes`). Задачи Celery переживают перезапуск.
- **JWT ключи** — volume `jwt_keys`. Генерируются один раз при первом `docker compose up`.

---

## Логирование

Логи пишутся в файлы с ротацией (5 МБ × 3 файла) и в консоль:

| Сервис | Файл лога |
|---|---|
| Django | `django_service/logs/django.log` |
| FastAPI | `fastapi_service/logs/fastapi.log` |

Формат: `2026-05-08 20:00:00 [INFO] apps.analysis: Анализ запущен...`

В режиме `DEBUG=True` — уровень DEBUG (все сообщения). В продакшне — INFO.

---

## Паттерны проектирования

Описание паттернов: [`patterns.txt`](patterns.txt)

- **Factory Method** — `IndicatorFactory.create()` создаёт нужный индикатор по имени
- **Template Method** — `BaseIndicator` задаёт общий интерфейс всех индикаторов
- **Strategy** — торговая стратегия как набор взаимозаменяемых условий AND/OR

---

## Тестирование

Проект покрыт тестами на двух сервисах:
- **Django** — через **Django Test Framework** (unittest-совместимый)
- **FastAPI** — через стандартный **unittest** + **httpx** (TestClient)

---

### 🐳 Запуск тестов всего проекта через Docker

#### Django-сервис

```bash
# Все тесты Django
docker compose exec django python manage.py test apps

# Тесты отдельного приложения
docker compose exec django python manage.py test apps.tickers
docker compose exec django python manage.py test apps.users
docker compose exec django python manage.py test apps.strategies
docker compose exec django python manage.py test apps.analysis
```

#### FastAPI-сервис

```bash
# Все тесты FastAPI
docker compose exec fastapi python -m unittest discover -s tests -p "test_*.py" -v
```

---

### 📊 Coverage (покрытие кода) через Docker

#### Django — coverage отчёт

```bash
# 1. Запустить тесты с замером покрытия
docker compose exec django coverage run manage.py test apps

# 2. Вывести отчёт в терминал
docker compose exec django coverage report

# 3. (Опционально) HTML-отчёт — открыть в браузере
docker compose exec django coverage html
```

HTML-отчёт появится в `django_service/htmlcov/index.html`.

#### FastAPI — coverage отчёт

```bash
# 1. Запустить тесты с замером покрытия
docker compose exec fastapi coverage run -m unittest discover -s tests -p "test_*.py"

# 2. Вывести отчёт в терминал
docker compose exec fastapi coverage report

# 3. (Опционально) HTML-отчёт
docker compose exec fastapi coverage html
```

HTML-отчёт появится в `fastapi_service/htmlcov/index.html`.

#### Суммарный отчёт по всему проекту

> ⚠️ **Windows PowerShell**: оператор `&&` не поддерживается. Выполняйте команды **по одной**:

```powershell
# Шаг 1 — Django: запустить тесты
docker compose exec django coverage run manage.py test apps

# Шаг 2 — Django: показать отчёт
docker compose exec django coverage report

# Шаг 3 — FastAPI: запустить тесты
docker compose exec fastapi coverage run -m unittest discover -s tests -p "test_*.py"

# Шаг 4 — FastAPI: показать отчёт
docker compose exec fastapi coverage report
```

---

### Запуск тестов локально (PowerShell)

```powershell
# Django
cd django_service
pip install -r requirements-dev.txt
python manage.py test apps
coverage run manage.py test apps
coverage report

# FastAPI
cd ..
cd fastapi_service
pip install -r requirements-dev.txt
python -m unittest discover -s tests -p "test_*.py" -v
coverage run -m unittest discover -s tests -p "test_*.py"
coverage report
```

---

### Структура тестов

| Сервис | Файл | Что покрывает |
|---|---|---|
| Django `tickers` | `apps/tickers/tests.py` | Модель Ticker, форма TickerForm, views (list, add, delete, bulk) |
| Django `users` | `apps/users/tests.py` | Профиль, формы регистрации и баланса, login/logout/register |
| Django `strategies` | `apps/strategies/tests.py` | Модели Strategy/StrategyCondition, `to_fastapi_config`, CRUD views |
| Django `analysis` | `apps/analysis/tests.py` | Модель AnalysisRun, поля, связи, API-вызовы |
| FastAPI `analyze_engine` | `tests/test_analyze_engine.py` | Парсинг конфига, индикаторы, оценка условий, публичный API |
| FastAPI `main` | `tests/test_main.py` | Эндпоинты `/chart-data`, `/analyze/`, `/analyze/status/`, `/analyze-one/` |

---


## Генерация документации (Sphinx)

Документация генерируется из docstring-ов в коде с помощью Sphinx.

### Установка и генерация

```bash
pip install sphinx

cd docs
sphinx-build -b html . _build/html
```

Готовая документация открывается в браузере:

```
docs/_build/html/index.html
```
