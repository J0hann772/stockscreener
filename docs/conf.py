# Configuration file for the Sphinx documentation builder.
import os
import sys

# Добавляем пути к исходникам
sys.path.insert(0, os.path.abspath('../fastapi_service'))
sys.path.insert(0, os.path.abspath('../django_service'))

# Мокаем все внешние зависимости, которых нет в системном Python
# Это позволяет Sphinx импортировать модули без установки pandas, celery и т.д.
autodoc_mock_imports = [
    'django',
    'dotenv',
    'celery',
    'redis',
    'fastapi',
    'pydantic',
    'yfinance',
    'pandas',
    'pandas_ta',
    'httpx',
    'jwt',
    'cryptography',
]

project = 'MarketView'
copyright = '2026, НИУ ВШЭ S102'
author = (
    'Буряк С.В., Салтанова С.А., Гавришов Е.А., Агапченко Н.Н., '
    'Гурская В.В., Новикова М.А., Ларионова П.Г., Симонов В.М., Азизов М.К.'
)
release = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

napoleon_google_docstring = False
napoleon_numpy_docstring = False

templates_path = ['_templates']
exclude_patterns = ['_build']

language = 'ru'
html_theme = 'alabaster'
html_static_path = ['_static']
