
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent

#SECRET_KEY ve DEBUG artık ortam değişkeninden okunuyor. Render'da (canlı ortam) bunlar
#gerçek/güvenli değerlerle set edilecek; ortam değişkeni yoksa (kendi bilgisayarımda
#çalıştırırken) eski sabit değerler devreye giriyor, yani yerelde hiçbir şey değişmiyor
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-kik^^=x2zzye8m%7_8279@li3d1eu)@l7=f*5cmexqh@hsm5$1')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS: list[str] = []

#Render deploy edince uygulamaya kendi alan adını bu ortam değişkeniyle bildiriyor,
#biz de onu ALLOWED_HOSTS'a ve CSRF_TRUSTED_ORIGINS'e ekliyoruz - yoksa Render hem
#siteyi 400 Bad Request ile reddeder hem de login/logout gibi POST formları CSRF
#hatası verir (Render TLS'i kendi tarafında sonlandırıp bize http olarak iletiyor)
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    #statik dosyaları (css/js/resim) Render gibi ortamlarda ayrı bir sunucu olmadan
    #doğrudan Django üzerinden hızlı ve sıkıştırılmış şekilde servis ediyor
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES: list[dict[str, Any]] = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ["templates"],
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




DATABASES: dict[str, dict[str, Any]] = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}




AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True



STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
#collectstatic'in topladığı dosyalar burada birikiyor, whitenoise buradan servis ediyor
STATIC_ROOT = BASE_DIR / 'staticfiles'

#canlıda (DEBUG=False) whitenoise'un sıkıştırıp önbelleklenebilir hale getirdiği
#statik dosya deposunu kullanıyoruz, yerelde eski basit yöntem yeterli
if not DEBUG:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
LOGIN_REDIRECT_URL = 'post_login_redirect'
LOGOUT_REDIRECT_URL = 'login'
ONE_WAY_FEE = 500