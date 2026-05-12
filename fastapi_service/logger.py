"""
Модуль настройки логирования для FastAPI-сервиса.

Настраивает два обработчика: консоль и RotatingFileHandler.
В DEBUG-режиме уровень логирования — DEBUG, иначе — INFO.
"""
import logging
import logging.handlers
import os
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parent.parent / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

_FMT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
_DATE_FMT = '%Y-%m-%d %H:%M:%S'


def setup_logging() -> None:
    """
    Инициализирует систему логирования.

    Настраивает корневой логгер с двумя обработчиками:
    - StreamHandler (консоль)
    - RotatingFileHandler (файл fastapi.log, ротация 5 МБ × 3 файла)

    Вызывается один раз при старте приложения.
    """
    formatter = logging.Formatter(_FMT, datefmt=_DATE_FMT)

    # Консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(LOG_LEVEL)

    # Файл с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'fastapi.log',
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # в файл пишем всё

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Не дублировать если уже настроен
    if not root.handlers:
        root.addHandler(console_handler)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает именованный логгер для модуля.

    Args:
        name (str): имя модуля (передавайте __name__).

    Returns:
        logging.Logger: настроенный логгер.
    """
    return logging.getLogger(name)
