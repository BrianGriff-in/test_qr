from pathlib import Path
from decouple import config
import dj_database_url
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-8$i^*($cxe#suzakeaqw1y49l=5k-n$v_rcjc169twa7@2mlq7')
DEBUG      = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'payments',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'khqr_demo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'khqr_demo.wsgi.application'

# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Phnom_Penh'
USE_I18N      = True
USE_TZ        = True

# ── Static files ───────────────────────────────────────────────────────────────
STATIC_URL       = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── KHQR ───────────────────────────────────────────────────────────────────────
KHQR_BANK_ACCOUNT   = config('KHQR_BANK_ACCOUNT',   default='yourname@acleda')
KHQR_MERCHANT_NAME  = config('KHQR_MERCHANT_NAME',  default='My Shop')
KHQR_MERCHANT_CITY  = config('KHQR_MERCHANT_CITY',  default='Phnom Penh')
KHQR_WEBHOOK_SECRET = config('KHQR_WEBHOOK_SECRET', default='dev-secret')
KHQR_PHONE_NUMBER   = config('KHQR_PHONE_NUMBER',   default='85512345678')
BAKONG_TOKEN        = config('BAKONG_TOKEN',         default='')

# ── CSRF ───────────────────────────────────────────────────────────────────────
NGROK_URL = config('NGROK_URL', default='')

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
if NGROK_URL:
    CSRF_TRUSTED_ORIGINS.append(NGROK_URL)

RENDER_URL = config('RENDER_URL', default='')
if RENDER_URL:
    CSRF_TRUSTED_ORIGINS.append(RENDER_URL)

# ── Security (production only) ─────────────────────────────────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE   = True
    CSRF_COOKIE_SECURE      = True