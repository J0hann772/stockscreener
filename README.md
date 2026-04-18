# Аналитическая платформа (Django + FastAPI)

## Описание архитектуры

Проект построен на базе микросервисной архитектуры и включает в себя следующие независимые компоненты:

- **Django (Основной бэкенд)** — монолитное ядро для управления пользователями (users), тикерами (tickers), стратегиями (strategies) и общим анализом (analysis). Работает по WSGI/ASGI.
- **FastAPI (Сервис аналитики)** — высокопроизводительный асинхронный микросервис. Общается с Django по HTTP.
- **PostgreSQL** — основная реляционная база данных.
- **Redis** — кэш ответов yfinance с персистентностью через AOF.

Сервисы общаются между собой по HTTP внутри сети `internal`. Redis используется исключительно как кэш, а не как транспорт между сервисами.

---

## Структура проекта

```
stockscreener/
├── django_service/
├── fastapi_service/
├── .env                         # переменные для docker-compose (DB credentials)
├── .env.django                  # переменные окружения для Django контейнера
├── .env.fastapi                 # переменные окружения для FastAPI контейнера
├── docker-compose.yml
├── docker-compose.override.yml  # автоматически подхватывается в dev-окружении
└── README.md
```

---

## Предварительная настройка

В корне проекта необходимо создать три конфигурационных файла.

**Файл `.env`** — переменные для подстановки в `docker-compose.yml`:

```env
DB_NAME=my_db
DB_USER=db_user
DB_PASSWORD=db_password
```

**Файл `.env.django`** — переменные окружения Django контейнера:

```env
SECRET_KEY=mysecretkey
DEBUG=True

DB_NAME=my_db
DB_USER=db_user
DB_PASSWORD=db_password
DB_HOST=postgres
DB_PORT=5432
```

**Файл `.env.fastapi`**:

```env
DEBUG=True
REDIS_URL=redis://redis:6379/0
INTERNAL_API_KEY=default-internal-key-for-dev
```

> **Почему три файла?** Docker Compose читает `${}` подстановки только из `.env`. Файлы `.env.django` и `.env.fastapi` передаются внутрь контейнеров через директиву `env_file`.

### Внутренняя безопасность (Internal API Key)

Для защиты общения между сервисами мы используем `INTERNAL_API_KEY`. Django сервис передает его в заголовке `X-Internal-Key`, а FastAPI проверяет его. Это гарантирует, что запросы на анализ акций приходят только от нашего бэкенда. По умолчанию используется значение `default-internal-key-for-dev`.

### Генерация RSA ключей (для аутентификации)

Перед запуском проекта необходимо сгенерировать приватные и публичные ключи, которые используются для подписи и проверки JWT токенов между Django и FastAPI.
Убедитесь, что у вас установлен Python, и запустите скрипт из корня проекта:

```bash
python generate_keys.py
```

Скрипт автоматически создаст папку `keys/` и разложит публичный и приватный ключи по нужным дирекриям (`django_service/keys/` и `fastapi_service/keys/`), чтобы контейнеры могли получить к ним доступ через volumes.

---

## Управление контейнерами

`docker-compose.override.yml` подхватывается Docker Compose **автоматически** при наличии в директории. Он монтирует локальные директории внутрь контейнеров и активирует горячую перезагрузку (Hot Reloading).

Если нужно запустить **без** override (например, для теста прод-конфига):

```bash
docker compose -f docker-compose.yml up
```

**Запуск локального окружения:**

```bash
docker compose up --build
```

**Остановка с сохранением данных:**

```bash
docker compose down
```

**Остановка с полным удалением данных БД:**

```bash
docker compose down -v
```

---

## Инициализация проекта

При первом запуске необходимо применить миграции и создать суперпользователя. Выполняется во **втором терминале**, пока `docker compose up` запущен в первом.

```bash
docker compose exec django python manage.py makemigrations
docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser
```

---

## Доступные сервисы и маршруты

| Сервис       | URL                                   |
| ------------ | ------------------------------------- |
| Django       | http://localhost:8000                 |
| Админ-панель | http://localhost:8000/admin/          |
| Авторизация  | http://localhost:8000/auth/           |
| Тикеры       | http://localhost:8000/api/tickers/    |
| Стратегии    | http://localhost:8000/api/strategies/ |
| Аналитика    | http://localhost:8000/api/            |
| FastAPI      | http://localhost:8001                 |

---

## Подключение к БД из IDE

В `docker-compose.yml` PostgreSQL пробрасывается на порт `5434` хост-машины (порты `5432` и `5433` могут быть заняты другими проектами).

```yaml
ports:
  - "5434:5432" # ХОСТ:КОНТЕЙНЕР
```

**Настройки подключения в IDE:**

| Параметр | Значение    |
| -------- | ----------- |
| Host     | localhost   |
| Port     | 5434        |
| User     | db_user     |
| Password | db_password |
| Database | my_db       |

---

## Управление зависимостями

Зависимости разделены на базовые (`requirements.txt`) и dev-инструменты (`requirements-dev.txt`).

Для добавления новой библиотеки: впишите её в нужный `requirements.txt` и пересоберите контейнер.

```bash
# Django
docker compose up -d --build django

# FastAPI
docker compose up -d --build fastapi
```

---

## Персистентность данных

- **PostgreSQL** — данные хранятся в именованном volume `postgres_data`. Удаляются только при `docker compose down -v`.
- **Redis** — включён режим AOF (`--appendonly yes`) с volume `redis_data`. Данные переживают перезапуск контейнера, так как Redis пишет каждую операцию на диск, а volume сохраняет файл между перезапусками.
