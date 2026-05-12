from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '..', '.env'))









# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

SECRET_KEY = os.getenv('SECRET_KEY')



# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() == 'true'

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "django"]

# JWT Keys configuration (RSA RS256)
KEYS_DIR = BASE_DIR / 'keys'
private_key_path = KEYS_DIR / 'private.pem'
public_key_path = KEYS_DIR / 'public.pem'

if not private_key_path.exists() or not public_key_path.exists():
    try:
        import subprocess
        import sys
        script_path = BASE_DIR.parent / 'generate_keys.py'
        if script_path.exists():
            print("Keys not found. Auto-generating via generate_keys.py...")
            subprocess.run([sys.executable, str(script_path)], check=True)
    except Exception as e:
        print(f"Warning: Could not auto-generate keys: {e}")

try:
    with open(private_key_path, 'rb') as f:
        JWT_PRIVATE_KEY = f.read()
    with open(public_key_path, 'rb') as f:
        JWT_PUBLIC_KEY = f.read()
except FileNotFoundError:
    print("WARNING: RSA keys not found in 'keys/' directory. Run 'python generate_keys.py'.")
    JWT_PRIVATE_KEY = b""
    JWT_PUBLIC_KEY = b""

JWT_TTL_MINUTES = 60 * 24 # 1 day

# Ключ для общения между Django и FastAPI
INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', 'default-internal-key-for-dev')

# URL FastAPI-сервиса (внутренняя сеть Docker)
FASTAPI_URL = os.getenv('FASTAPI_URL', 'http://fastapi:8001')

LOGIN_URL = 'login'


# Application definition
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'django']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.analysis',
    'apps.users',
    'apps.tickers',
    'apps.strategies',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'my_db'),
        'USER': os.getenv('DB_USER', 'db_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'pass123'),
        'HOST': os.getenv('DB_HOST', 'postgres'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'https://www.tradingview.com',
    'https://s3.tradingview.com',
    'https://www.tradingview-widget.com',
]
CSRF_COOKIE_SECURE = False

# Разрешаем TradingView встраивать iframes (для страницы графиков)
X_FRAME_OPTIONS = 'SAMEORIGIN'  # стандартное значение, xframe_options_exempt снимает для конкретных view

# ── Логирование ─────────────────────────────────────────────────────────────
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 3,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
